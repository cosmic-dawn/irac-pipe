#!/bin/sh
# count _bcd files in each AOR, by channel
# AMo - Dec.18
#-----------------------------------------------------------------------------

#root=/n08data/Spitzer
#root=/n08data/NEP/Data
#cd $root

#---------------------------------------------------------------------------
# build list of AORs
#---------------------------------------------------------------------------

if [ $1 == "dirs" ]; then
    #for d in [C-X]*; do 
	for d in NEP*; do 
		rm -f ~/ListDirs_${d}.txt
		echo " >> build directory list for $d"
		ls -d $d/r*/ch? > ~/ListDirs_${d}.txt
	done
fi
#---------------------------------------------------------------------------
# count num bcd files in each AOR, and by channel
#---------------------------------------------------------------------------

if [ $1 == "aors" ]; then
for d in [C-X]*; do 
#for d in NEP*; do 
	rm -f ~/FileCount_${d}.txt
	echo " >> begin AOR count of $(ls -d $d/r* | wc -l) AORs in $d"
	for aor in $d/r*; do 
		root=$(echo $aor | cut -d\/ -f1-3 )
		n1=$(ls $root/ch1/bcd/SPI*_bcd.fits 2> /dev/null | wc -l)
		n2=$(ls $root/ch2/bcd/SPI*_bcd.fits 2> /dev/null | wc -l)
		n3=$(ls $root/ch3/bcd/SPI*_bcd.fits 2> /dev/null | wc -l)
		n4=$(ls $root/ch4/bcd/SPI*_bcd.fits 2> /dev/null | wc -l)
		echo "$root $n1 $n2 $n3 $n4" | \
			awk '{printf "%-9s: %4i %4i %4i %4i  %5i\n", $1,$2,$3,$4,$5,$2+$3+$4+$5 }' \
			>> ~/FileCount_${d}.txt
	done 
done
fi

#---------------------------------------------------------------------------
# count num files of each type and give warning if not equal
#---------------------------------------------------------------------------

HOME=/n08data/Spitzer
if [ $1 == "files" ]; then
#	for d in [C-X]*; do 
	for d in NEP; do 
		rm -f ~/FileCount_${d}.txt
		echo " >> begin file count of $(ls -d $d/r* | wc -l) AORs in $d"
		for aor in $d/r*; do 
			root=$(echo $aor | cut -d\/ -f1-3 )
			cd $root   #; echo " --> $PWD"
			for c in ch?; do
				n1=$(ls $c/bcd/SPI*_bcd.fits   2> /dev/null | wc -l)
				n2=$(ls $c/bcd/SPI*_bimsk.fits 2> /dev/null | wc -l)
				n3=$(ls $c/bcd/SPI*_bunc.fits  2> /dev/null | wc -l)
				n4=$(ls $c/bcd/SPI*_cbcd.fits  2> /dev/null | wc -l)
				n5=$(ls $c/bcd/SPI*_cbunc.fits 2> /dev/null | wc -l)
				if [ $n1 -ne $n2 ] || [ $n1 -ne $n3 ] || [ $n1 -ne $n4 ] || [ $n1 -ne $n5 ]; then
					echo -n "## something missing in "
					echo "$root/$c $n1 $n2 $n3 $n4 $n5" | awk \
						'{printf "%-12s: %4i %4i %4i %4i %4i\n", $1,$2,$3,$4,$5,$6 }'
				fi
			done
			cd $HOME
		done
	done
fi

#---------------------------------------------------------------------------
# get coords of first ch? file of each AOR (almost) and also aorhdr kwd
#---------------------------------------------------------------------------

if [ $1 == "coords" ]; then
	for d in [C-X]*; do 
		outfile=/home/moneti/Coords_${d}.tbl # 	rm -f $outfile
		dfits $d/r*/ch?/bcd/*0000_0000_?_bcd.fits | fitsort -d crval1 crval2 aorhdr > $outfile &
	done
fi

#---------------------------------------------------------------------------
# Number of frames of each chan  from Frames.tbl
#---------------------------------------------------------------------------


if [ $1 == "frames" ]; then
	odir=$(grep 'OutputDIR  =' supermopex.py | cut -d\' -f2 | tr -d \/)
	ltab=$(grep 'LogTable ='   supermopex.py | cut -d\' -f2)
	Nframes=$(grep -v '^|' $odir/$ltab | wc -l)
	echo " Num images: $Nframes"
	for c in 1 2 3 4; do
		echo " - in Ch${c}:  $(grep _I${c}_ $odir/$ltab | wc -l)"
	done
fi
