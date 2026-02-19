import logging
import subprocess

logger = logging.getLogger(__name__)


class RoughCutError(Exception):
    """Base exception for rough-cut errors"""
    pass


def run_command(cmd, description, capture_output=False, check=True):
    """Run a shell command with error handling"""
    logger.info(f"{description}...")
    try:
        if capture_output:
            result = subprocess.run(cmd, capture_output=True, text=True, check=check, shell=isinstance(cmd, str))
            return result
        else:
            subprocess.run(cmd, check=check, shell=isinstance(cmd, str))
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed: {' '.join(cmd) if isinstance(cmd, list) else cmd}")
        if capture_output and e.stderr:
            logger.error(f"Error: {e.stderr}")
        raise RoughCutError(f"Failed: {description}")
