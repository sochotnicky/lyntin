#!/usr/bin/env python
#######################################################################
# This file is part of Lyntin.
# copyright (c) Free Software Foundation 2001, 2002
#
# Lyntin is distributed under the GNU General Public License license.  See the
# file LICENSE for distribution details.
# $Id: runlyntin.pyw,v 1.1 2003/10/03 02:17:48 willhelm Exp $
#######################################################################
bootoptions = {"ui": "tk",
               "datadir": "",
               "moduledir": [],
               "readfile": [],
               "snoopdefault": 1}

if __name__ == '__main__':
  import lyntin.engine
  lyntin.engine.main(bootoptions)

# Local variables:
# mode:python
# py-indent-offset:2
# tab-width:2
# End:
