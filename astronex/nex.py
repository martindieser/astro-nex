#!/usr/bin/python
# -*- coding: utf-8 -*-
import sys, os
import glob
import gettext
import atexit
from . import countries
from .config import read_config
lang_es = gettext.translation('astronex','./astronex/translations', languages=['es'])
lang_en = gettext.translation('astronex','./astronex/translations', languages=['en'])
lang_ca = gettext.translation('astronex','./astronex/translations', languages=['ca'])
lang_de = gettext.translation('astronex','./astronex/translations', languages=['de'])
langs = { 'en': lang_en, 'es': lang_es, 'ca': lang_ca, 'de': lang_de }

from astronex.compat import Gtk, Gdk, GObject, GdkPixbuf
from path import Path
version = "1.2"

def die(message):
    """Die in a command line way."""
    sys.exit(1)

# Python 2.5
if sys.version_info < (2,5):
    die('Python 2.5 is required to run Astro-Nex. Only %s.%s was found.' %
            sys.version_info[:2])


home_dir = '.astronex'
config_file = 'cfg.ini'
default_db = 'charts.db'
ephe_path = 'ephe'
ephe_flag = 4

def check_home_dir(appath):
    """Set home dir, copying needed files"""
    global home_dir, ephe_flag
    default_home = Path.joinpath(Path.expanduser(Path('~')), home_dir)

    if not Path.exists(default_home):
        Path.mkdir(default_home)
    ephepath = Path.joinpath(default_home,ephe_path)
    if not Path.exists(ephepath):
        Path.mkdir(Path.joinpath(default_home,ephe_path))
        Path.copy(Path.joinpath(appath,"astronex/resources/README"),ephepath)
    if ephepath.glob("*.se1"):
        ephe_flag = 2
    if not Path.exists(Path.joinpath(default_home,default_db)):
        Path.copy(Path.joinpath(appath,"astronex/resources/charts.db"),default_home)

    home_dir = default_home


def init_config(homedir,opts,state):
    ephepath = Path.joinpath(homedir,opts.ephepath)
    from pysw import setpath
    setpath(str(ephepath))

    state.country = opts.country
    state.usa = {'false':False,'true':True}[opts.usa]
    state.database = opts.database
    state.setloc(opts.locality,opts.region)
    state.init_nowchart()
    state.curr_chart = state.now
    state.epheflag = ephe_flag
    opts.epheflag = ephe_flag

    if opts.favourites:
        try:
            tbl = opts.favourites
            nfav = int(opts.nfav)
            favs = state.datab.get_favlist(tbl,nfav,state.newchart())
            state.fav = favs
        except:
            pass

    from .chart import orbs as ch_orbs
    orbs = [opts.lum,opts.normal,opts.short,opts.far,opts.useless]
    for l in orbs:
        state.orbs.append(list(map(float,l)))
        ch_orbs.append(list(map(float,l)))
    peorbs = [opts.pelum,opts.penormal,opts.peshort,opts.pefar,opts.peuseless]
    for l in peorbs:
        state.peorbs.append(list(map(float,l)))
    for l in opts.transits:
        state.transits.append(float(l))
    opts.discard = [ int(x) for x in opts.discard ]

class Splash (Gtk.Window):
    def __init__(self,appath):
        Gtk.Window.__init__(self,Gtk.WindowType.POPUP)
        self.set_default_size(400, 250)
        self.set_position (Gtk.WindowPosition.CENTER)
        vbox = Gtk.VBox()
        img = Gtk.Image()
        splashimg = Path.joinpath(appath,"astronex/resources/splash.png")
        img.set_from_pixbuf(GdkPixbuf.Pixbuf.new_from_file(splashimg))
        vbox.pack_start(img, True, True, 0)
        self.add(vbox)

def init_ipshell():
    ''' ipython suport (for linux)'''
    if sys.platform != 'win32':
        try:
            __IPYTHON__
        except NameError:
            argv = ['']
            banner = exit_msg = ''
        else:
            argv = ['-pi1','In <\\#>:','-pi2','   .\\D.:','-po','Out<\\#>:']
            banner = '*** Nested interpreter ***'
            exit_msg = '*** Back in main IPython ***'

        #from IPython.Shell import IPShellEmbed
        #ipshell = IPShellEmbed(argv,banner=banner,exit_msg=exit_msg)
        #return ipshell
        from IPython.config.loader import Config
        cfg = Config()
        cfg.InteractiveShellEmbed.prompt_in1="myprompt [\\#]> "
        cfg.InteractiveShellEmbed.prompt_out="myprompt [\\#]: "
        #cfg.InteractiveShellEmbed.profile=ipythonprofile
        from IPython.frontend.terminal.embed import InteractiveShellEmbed
        shell = InteractiveShellEmbed(config=cfg, banner2=banner)
        shell.user_ns = {}
        return shell

class application(object):
    """The Nex Application."""

    def __init__(self,appath):
        self.home_dir = home_dir
        self.config_file = config_file
        self.default_db = default_db
        self.appath = appath
        self.version = version
        self.langs = langs

    def run(self):
        """Start Nex"""
        splash = Splash(self.appath)
        splash.show_all()
        GObject.timeout_add(1000, splash.hide) # 5*1000 miliseconds
        GObject.idle_add(self.setup_app)
        Gtk.main()

    def run_console(self):
        opts = read_config(self.home_dir)
        opts.home_dir = self.home_dir
        langs[opts.lang].install()
        countries.install(opts.lang)
        self.lang = opts.lang
        from .state import Current
        from .boss import Manager
        state = Current(self)
        init_config(self.home_dir,opts,state)
        boss = Manager(self,opts,state)
        boss.ipshell = init_ipshell()
        boss.ipshell()

    def setup_app(self):
        opts = read_config(self.home_dir)
        opts.home_dir = self.home_dir
        langs[opts.lang].install()
        countries.install(opts.lang)
        self.lang = opts.lang
        from .state import Current
        from .boss import Manager
        state = Current(self)
        atexit.register(state.save_pool,self)
        init_config(self.home_dir,opts,state)
        boss = Manager(self,opts,state)
        from .gui.winnex import WinNex
        mainwin = WinNex(boss)
        boss.set_mainwin(mainwin)
        #if 'DEBUG_NEX' in os.environ:
        #    boss.ipshell = init_ipshell()

    def stop(self):
        """Stop Nex."""
        Gtk.main_quit()

def main(appath,console=False):
    check_home_dir(appath)
    app = application(appath)
    if console:
        app.run_console()
    else:
        app.run()

