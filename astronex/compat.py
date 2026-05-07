import gi
gi.require_version('Gtk', '3.0')
gi.require_version('PangoCairo', '1.0')
from gi.repository import Gtk, Gdk, GObject, GdkPixbuf
from gi.repository import Pango as pango
from gi.repository import PangoCairo as pangocairo
import cairo