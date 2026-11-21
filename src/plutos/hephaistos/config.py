#
# hephaistos/config.py
#

import os
from pathlib import Path
from . import models

START_OFFSET = 10 * 60 # don't begin trading bevor this offset in seconds since start of the session
CANDLE_SIZE  = 36 # size of a candle
TREND_LENGTH = 5 # length of trend (in candles) to be labeled
RISK         = 24 # maximum risk to be taken (in ticks)
PROFIT       = 48 # profit to be achieved (in ticks)
WINDOW_SIZE  = 12 # size of tripple barrier window in candles

DATABENTO_DIR  = Path(os.environ.get('DATABENTO_DIR', '.'))

HEPHAISTOS_DIR = Path(os.environ.get('HEPHAISTOS_DIR', '.'))
TRAINING_DIR   = HEPHAISTOS_DIR/'training'
EVAL_DIR       = HEPHAISTOS_DIR/'eval'
TEST_DIR       = HEPHAISTOS_DIR/'test'

MODEL_PATH = Path(models.__file__).resolve().parent

PROBABILITY_THRESHOLD = 0.30 # threshold probability for trades
