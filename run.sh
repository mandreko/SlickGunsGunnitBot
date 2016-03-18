#!/bin/bash

process=slickgunsbot.py
makerun="python /home/<user>/SlickGunsGunnitBot/slickgunsbot.py"

if ps ax | grep -v grep | grep $process > /dev/null
then
      exit
    else
          $makerun &
        fi

        exit
fi
