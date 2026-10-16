#!/bin/zsh
# Freerouting on a DSN from fr_prep.py:  hardware/tools/fr_run.sh run.dsn run.ses [passes]
# Power nets (class NOROUTE) are left alone, no neckdown below the class width, strict DRC.
JAR=${FREEROUTING_JAR:-$HOME/.local/share/freerouting/freerouting.jar}
java -jar $JAR -de $1 -do $2 -mp ${3:-20} -mt 8 --gui.enabled=false \
  --router.autorouter.ignore_net_classes=NOROUTE --router.automatic_neckdown=false --router.strict_drc=true
