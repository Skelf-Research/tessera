"""
Tessera service entry point.
"""

from .web import TesseraService


def main():
    """Main entry point for the Tessera service."""
    service = TesseraService()
    service.run()


if __name__ == '__main__':
    main()