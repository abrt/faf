CDDIR=$(dir $(firstword $(MAKEFILE_LIST)))

srpm:
	dnf -y install autoconf automake autogen libtool
	cd $(CDDIR)..;./autogen.sh; ./configure
	make -C $(CDDIR).. srpm
	cp $(CDDIR)../*src.rpm $(outdir)
