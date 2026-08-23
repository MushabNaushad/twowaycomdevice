#!/usr/bin/sh
export VOLK_GENERIC=1
export GR_DONT_LOAD_PREFS=1
export srcdir=/home/mushabmna/Documents/twowaycomdevice/blocks/gr-transport/python/transport
export GR_CONF_CONTROLPORT_ON=False
export PATH="/home/mushabmna/Documents/twowaycomdevice/blocks/gr-transport/build/python/transport":"$PATH"
export LD_LIBRARY_PATH="":$LD_LIBRARY_PATH
export PYTHONPATH=/home/mushabmna/Documents/twowaycomdevice/blocks/gr-transport/build/test_modules:$PYTHONPATH
/usr/bin/python3 /home/mushabmna/Documents/twowaycomdevice/blocks/gr-transport/python/transport/qa_transport_layer.py 
