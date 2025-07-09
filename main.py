import os
import sys
import webbrowser as www
import hou

from PySide2 import QtWidgets, QtGui, QtUiTools
from PySide2.QtWidgets import QMessageBox, QPushButton, QFileDialog, QListWidget, QAbstractItemView
from PySide2.QtCore import Qt



FILE_PATH = os.path.dirname(__file__)
IMG_UI = os.path.join(FILE_PATH, "resources/ui_banner.jpg")
UI_PATH = os.path.join(FILE_PATH, "main_ui.ui")

#Hou Contexts

obj = hou.node("/obj")

mat = hou.node("/mat")



class BatchAlembic:
    def __init__(self):
        
        #Load UI
        self.main_ui = QtUiTools.QUiLoader().load(UI_PATH)

        #ADD Banner to UI

        pixmap = QtGui.QPixmap(IMG_UI)
        self.main_ui.label_banner.setPixmap(pixmap)

        #class attrs
        self.abc_paths = {}

        self.matAttr = "shop_materialpath"

        self.mat_names = []
        
        self.mat_context = None

        self.mat_nodes = []

        self.created_materials = set()
        
        
        #----------Buttons----------
        
        #List Widget
        self.main_ui.listWidget.setSelectionMode(QAbstractItemView.ExtendedSelection)

        #QListWidget Buttons
        self.main_ui.btn_add_abc.clicked.connect(self.add_alembic_list)
        self.main_ui.btn_exc_abc.clicked.connect(self.exc_alembic_item)

        #Core Logic Buttons
        self.main_ui.btn_import.clicked.connect(self.import_alembics)
        self.main_ui.btn_mat_context.clicked.connect(self.jump_to_mat)

        #User Buttons
        self.main_ui.btn_info.clicked.connect(self.artist_infos)
        self.main_ui.btn_cancel.clicked.connect(self.ui_exit)

        #Checkboxes
        self.main_ui.chbx_full_path.toggled.connect(self.update_list_display)
        self.main_ui.chbx_mat_ovr.toggled.connect(self.override_material_attribute)

        #List Widget
        self.main_ui.listWidget.setSelectionMode(QAbstractItemView.ExtendedSelection)

        #Show the UI
        self.main_ui.show()
        
        #---------------------------

    
    def add_alembic_list(self):
        abc_paths, _ = QFileDialog.getOpenFileNames(self.main_ui, "Select Alembics", "", "Alembic (*.abc)")

        for path in abc_paths:
            if path not in self.abc_paths.values():
                abc_name = os.path.basename(path)
                self.abc_paths[abc_name] = path
                
                self.update_list_display(self.main_ui.chbx_full_path.isChecked())

    def update_list_display(self, show_full_path):
        self.main_ui.listWidget.clear()

        for name, path in self.abc_paths.items():
            item_text = path if show_full_path else name
            self.main_ui.listWidget.addItem(item_text)

    
    def exc_alembic_item(self):
        selected_items = self.main_ui.listWidget.selectedItems()
        if not selected_items:
            QMessageBox.warning(self.main_ui, "Warning", "Please, select the items that will be deleted.")
            return

        full_path_on = self.main_ui.chbx_full_path.isChecked()

        for item in selected_items:
            item_value = item.text()

            if full_path_on:

                item_to_remove = None
                
                for key, value in self.abc_paths.items():
                    if value == item_value:
                        item_to_remove = key
                        break
                if item_to_remove:
                    del self.abc_paths[item_to_remove]
            else:

                if item_value in self.abc_paths:
                    del self.abc_paths[item_value]
        
        for item in selected_items:
            self.main_ui.listWidget.takeItem(self.main_ui.listWidget.row(item))


    def override_material_attribute(self, checked):
        if checked:
            ovr_value = self.main_ui.l_edit_mat_ovr.text().strip()
            self.matAttr = ovr_value
        else:
            self.matAttr = "shop_materialpath"

    def import_alembics(self):

        #This method will import the alembic, fetch the abc's path for a custom material attribute or shop_materialpath and filter repetition.
        #For now, it will create basic arnold material builder. To be further enhanced with an automatic maps assignment.
        self.mat_names = []
        self.mat_nodes.clear()
        #Check for any material network in the obj context root.

        mat_query = [node.path() for node in obj.children() if node.type().name() == "matnet"]
        
        if self.mat_context:
            pass
        elif mat_query:
            self.mat_context = hou.node(mat_query[0]) #Will fetch the first mat network assuming the workflow centralizes the materials into one mat network per context, i'm choosing to centralize in the root... to be further developed with costumizations.
        else:
            mat_net = obj.createNode("matnet", node_name = "global_mat_network" )
            self.mat_context = mat_net #Here i'm just referencing the mat network to the ui class

        vex_code_custom_attr = f"""string attr_query = prim(0, "{self.matAttr}", @primnum);\ns@shop_materialpath = "{self.mat_context.path()}" + "/" + attr_query;\nremoveattrib(0, "primitive", "{self.matAttr}");"""

        vex_code_default_attr =f"""string attr_query = prim(0, "shop_materialpath", @primnum);\ns@shop_materialpath = "{self.mat_context.path()}" + "/" + attr_query;"""


        for abc_name, abc_path in self.abc_paths.items():
            abc_container = obj.createNode("geo", node_name = os.path.splitext(abc_name)[0] + "_import")

            abc_node = abc_container.createNode("alembic", node_name = os.path.splitext(abc_name)[0])
            abc_node.parm("fileName").set(abc_path)

            unpack = abc_container.createNode("unpack", node_name = "abc_unpack")
            unpack.setInput(0, abc_node)
            unpack.setDisplayFlag(True)
            unpack.setRenderFlag(True)
            unpack.setSelected(True, clear_all_selected = False)
            unpack.cook()

            abc_geo = unpack.geometry()

            attribute_query = abc_geo.findPrimAttrib(self.matAttr)
            
            if not attribute_query:
                QMessageBox.information(self.main_ui,
                "Missing Material Attribute",
                f"Material Attributes not found in {abc_name}! The process will continue without material creation.")
                unpack.destroy()
                abc_out = abc_container.createNode("null", node_name = os.path.splitext(abc_name)[0] + "_OUT")
                abc_out.setInput(0,abc_node)
                abc_out.setDisplayFlag(True)
                abc_out.setRenderFlag(True)
                abc_out.setSelected(True, clear_all_selected = False)
                abc_container.layoutChildren()
                obj.layoutChildren()
                continue

            if attribute_query.dataType() != hou.attribData.String:
                QMessageBox.critical(
                    self.main_ui,
                    "Invalid Data Type",
                    f"Attribute '{self.matAttr}' is not a string attribute. Expected material paths."
                )
                continue

            self.mat_names = list(set(attribute_query.strings()))

            for mat_name in self.mat_names:
                clean_name = os.path.basename(mat_name)

                if clean_name not in self.created_materials:
                    self.create_alembic_material(clean_name)
                    self.created_materials.add(clean_name)

            #If material tag attribute is not Houdini's default, it will trigger a wrangle node for renaming and faster performance for heavy files.
            vex_code = vex_code_default_attr if self.matAttr == "shop_materialpath" else vex_code_custom_attr

            vex_node = abc_container.createNode("attribwrangle", node_name = "material_pathing")
            vex_node.parm("class").set("primitive")
            vex_node.parm("snippet").set(vex_code)
            vex_node.setInput(0, unpack)

            pack = abc_container.createNode("pack", node_name = "abc_repack")
            pack.setInput(0,vex_node)

            abc_out = abc_container.createNode("null", node_name = os.path.splitext(abc_name)[0] + "_OUT")
            abc_out.setInput(0,pack)
            abc_out.setDisplayFlag(True)
            abc_out.setRenderFlag(True)
            abc_out.setSelected(True, clear_all_selected = False)
            abc_container.layoutChildren()
            obj.layoutChildren()

        

    def create_alembic_material(self, mat_name):
        
        if self.mat_context.node(mat_name):
            return
        
        mat_builder = self.mat_context.createNode("arnold_materialbuilder", node_name = mat_name)
        ai_surface = mat_builder.createNode("arnold::standard_surface", node_name = mat_name + "_surface")
        out = mat_builder.node("OUT_material")
        out.setInput(0, ai_surface)
        mat_builder.layoutChildren()
        self.mat_context.layoutChildren()
        self.mat_nodes.append(mat_builder.path())

    def jump_to_mat(self):
        net_editor = hou.ui.paneTabOfType(hou.paneTabType.NetworkEditor)
        target_node = hou.node(self.mat_nodes[0])
        net_editor.setCurrentNode(target_node)
        net_editor.homeToSelection()

    def artist_infos(self):    
        msg_box = QMessageBox(self.main_ui)
        msg_box.setIcon(QMessageBox.Information)
        msg_box.setWindowTitle("Artist Information")
        msg_box.setTextFormat(Qt.RichText)
        msg_box.setText(
            'This script was created by Ricky Monti.<br><br>'
            'Visit <a href="https://rickymonti.com">my portfolio</a>!'
        )
        msg_box.setTextInteractionFlags(Qt.TextBrowserInteraction)
        msg_box.exec_()

    def ui_exit(self):
        self.main_ui.close()


def create():
    app = QtWidgets.QApplication(sys.argv)
    main_widget = BatchAlembic()
    sys.exit(app.exec_())


# DCC start
def start():
    global main_widget
    main_widget = BatchAlembic()

if __name__ == "__main__":
    start()