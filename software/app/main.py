import logging

from utils import create_logger

if __name__ == "__main__":
    create_logger()
    logger = get_logger(__name__)

    app = FastAPI()