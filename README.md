# batch_abc_import
Simple script for batch importing abc files and creating simple materials.

You can specify your own material attribute name or use Houdini's default attribute "shop_materialpath".

Tested in Houdini 20.5, but it should work with previous versions.

## Installation ##

Choose your preferred path to store your scripts.

Copy the batch_abc_location json file to the Houdini's packages folder.

Alter the path to your root path.

Example:

```bash
{
    "env":[
        {
            "SCRIPT_PATH" : "C:\Tools\HOU\scripts"
        }
    ]

}
```

Finally, create a a shelf button with the following code

```bash
import sys
import os

script_path = os.getenv("SCRIPT_PATH")

if script_path not in sys.path:
    sys.path.append(script_path)

import batch_alembic_importer.main as abc_import

abc_import.start()
```

Hope your like it!

