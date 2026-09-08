import sys

from puma_ui.app import main
from puma_ui.package_smoke import packaged_smoke_main


if __name__ == "__main__":
    if "--smoke-test" in sys.argv:
        sys.exit(packaged_smoke_main(sys.argv[1:]))
    main()
