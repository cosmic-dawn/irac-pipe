#!/bin/sh
#-----------------------------------------------------------------------------
# build region files from gaia, wise, bright and refined tables
#-----------------------------------------------------------------------------

cd $WRK/Products

# GAIA:
grep -v '|' gaia.tbl |\
   awk '{printf "fk5;box (%0.6f, %0.6f,0.0013, 0.0013) #color=blue, width=2\n", $9,$11}' > gaia.reg
#   awk '{printf "fk5;box (%0.6f, %0.6f,0.0013, 0.0013) #color=blue, width=2, text={%19s}\n", $9,$11,$6}' > gaia.reg
echo ">> Built gaia.reg with $(cat gaia.reg | wc -l) entries"

# refined: bright stars that have been detected in one or more of the frames; use wiseID
grep -v '|' stars.refined.tbl |\
   awk '{printf "fk5;circle (%0.6f, %0.6f,0.0007) #color=yellow, width=3, text={%19s}\n", $2,$3,$1}' > refined.reg
echo ">> Built refined.reg with $(cat refined.reg | wc -l) entries"

#exit 0
# bright: wise stars brighter than BrightStar in w1 or w2; use wise ID
grep -v '|' bright_stars.tbl |\
   awk '{printf "fk5;annulus (%0.6f, %0.6f,0.0011, 0.0013) #color=green, width=2, text={%19s}\n", $3,$4,$2}' > bright.reg
echo ">> Built bright.reg with $(cat bright.reg | wc -l) entries"

# ALLWISE
grep -v '|' wise.tbl |\
   awk '{printf "fk5;circle (%0.6f, %0.6f,0.0007) #color=red, width=2, text={%19s}\n", $2,$3,$1}' > wise.reg
echo ">> Built wise.reg with $(cat wise.reg | wc -l) entries"

