from pi_server.utils.logger import get_logger

"""
===============================================================================

	Main

===============================================================================
"""

log = get_logger("server.log", console=True)

def main():
    log.info("Hello World!")

if __name__ == "__main__":
    main()
