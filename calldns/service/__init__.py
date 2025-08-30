"""
CallDNS service entry point.
"""

from .web import CallDNSService


def main():
    """Main entry point for the CallDNS service."""
    service = CallDNSService()
    service.run()


if __name__ == '__main__':
    main()