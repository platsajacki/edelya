from pathlib import Path

from core.utils import import_modules_from_package_dir

import_modules_from_package_dir(
    package_name=__name__,
    package_dir=Path(__file__).resolve().parent,
)
