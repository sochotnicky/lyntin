#######################################################################
# This file is part of Lyntin.
# copyright (c) Free Software Foundation 2001, 2002
#
# Lyntin is distributed under the GNU General Public License license.  See the
# file LICENSE for distribution details.
# $Id: __init__.py,v 1.3 2003/08/06 22:59:44 willhelm Exp $
#######################################################################
"""
This is the ui package.  Ui's to be used in Lyntin need to be dropped
in here.  ui's should extend the base.BaseUI class and should also
implement the get_ui_instance function that actually returns an instance 
of the ui in question.

See the textui and tkui code for examples.
"""
