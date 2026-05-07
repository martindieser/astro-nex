# -*- coding: utf-8 -*-
from astronex.compat import Gtk, Gdk, pango
from .. drawing.dispatcher import DrawMixin

class PlanSelector(Gtk.Dialog):
    '''Planet selector'''

    def __init__(self,parent):
        self.parnt = parent
        self.notwanted = set()
        self.plet = ['d','f','h','j','k','l','g','z','x','c','v']
        
        Gtk.Dialog.__init__(self,
                _("Selector de aspectos"), parent,
                Gtk.DialogFlags.DESTROY_WITH_PARENT,
                (Gtk.STOCK_CLOSE, Gtk.ResponseType.NONE,))

        #self.set_size_request(400,580)
        self.get_content_area().set_border_width(3)
        frame = Gtk.Frame(label=_("Ocultar"))
        frame.set_border_width(3)
        
        frame.add(self.create_buttonlist())
        self.get_content_area().pack_start(frame,False,False,0)
        
        self.connect("response", self.dlg_response)
        self.connect('key-press-event', self.on_key_press_event,parent) 

        self.show_all()
        self.parnt.da.redraw()

    def create_buttonlist(self):
        font = pango.FontDescription("Astro-Nex")
        vbuttonbox = Gtk.VButtonBox() 
        for let in self.plet:
            but = Gtk.ToggleButton(label=let)
            but.get_child().override_font(font)
            but.set_mode(True)
            but.connect("toggled",self.on_but_toggled)
            vbuttonbox.pack_start(but,False,False,0)
        return vbuttonbox

    def on_but_toggled(self,but):
        let = but.get_label()
        if but.get_active():
            self.notwanted.add(self.plet.index(let))
        else:
            self.notwanted.discard(self.plet.index(let))
        DrawMixin.notwanted = list(self.notwanted)
        self.parnt.da.redraw()
        self.parnt.da.redraw_auxwins() 

    def dlg_response(self,dialog,rid):
        self.parnt.boss.mpanel.toolbar.get_nth_item(3).set_active(False) 
        return
    
    def on_key_press_event(self,window,event,parent): 
        if event.keyval == Gdk.KEY_Escape:
            parent.boss.mpanel.toolbar.get_nth_item(3).set_active(False) 
        return True

    def exit(self):
        DrawMixin.notwanted  = []
        #self.parnt.da.drawer.notwanted
        self.parnt.da.redraw()
        self.parnt.da.plselector = None
        self.destroy()
