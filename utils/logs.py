import logging
import os

LOG_DIR = "./database/logs"

def setup_logger(module_name: str) -> logging.Logger:
    """
    Creates a separate log file for each script/module.
    """
    # Create logs directory if it doesn't exist
    os.makedirs(LOG_DIR, exist_ok=True)
    
    # Convert module name to safe filename
    safe_name = module_name.replace(".", "_").replace("/", "_").replace("\\", "_")
    
    # Create unique log filename for this module
    log_file = f"{LOG_DIR}/{safe_name}.log"
    
    # Create logger with the module name
    logger = logging.getLogger(module_name)
    logger.setLevel(logging.INFO)
    
    # Prevent adding multiple handlers if logger already exists
    if not logger.handlers:
        # Create file handler for this specific module
        file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)s | %(funcName)s:%(lineno)d | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler.setFormatter(formatter)
        
        # Add handler to logger
        logger.addHandler(file_handler)
        
        # IMPORTANT: Write an initial message to create the file immediately
        logger.info(f"=== Logger initialized for module: {module_name} ===")
        
        # Force flush to ensure the file is created
        for handler in logger.handlers:
            handler.flush()
    
    return logger