#! /usr/bin/env bash

#手动操作资产更新Debug启动方式，防止不同习惯，不同操作方式出现未知异常，可能会导致主程序卡死
python3 startup.py --service='hand_app' --port='8051'