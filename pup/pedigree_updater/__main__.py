
import sys


def main():
    if __package__ == '':
        # Running as a wheel (easy deployment for eg Pedigree repo builds)
        import os.path
        me = os.path.dirname(os.path.dirname(__file__))
        sys.path[0:0] = [me]

    import pedigree_updater.frontend.main
    return pedigree_updater.frontend.main.main()


if __name__ == '__main__':
    sys.exit(main())
