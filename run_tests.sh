#!/bin/sh

echo "Testing CS640 - Project 1 - Part 1"

swyard -t lru_test.srpy myswitch_lru.py

echo "Testing CS640 - Project 1 - Part 2"

swyard -t myswitchstp_test_release.py myswitch_stp.py
