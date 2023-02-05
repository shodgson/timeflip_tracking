# timeflip_tracking
A very unofficial python script to read current data from a TimeFlip device (https://timeflip.io/)

### Usage
```sh
./timeflip.py --address "TIMEFLIP_BLUETOOTH_ADDRESS" -o OUTPUT.CSV
```

### Description
When the TimeFlip device is connected, each turn of the device will trigger a notification. This will be logged in the `output.csv` file with four fields:
- Starting timestamp
- Activity name (as set in the `activities` array)
- Ending timestamp
- Duration (in seconds)

### Credit
Thanks to [Pierre Beaujean](https://github.com/pierre-24/pytimefliplib) for doing the hard work
