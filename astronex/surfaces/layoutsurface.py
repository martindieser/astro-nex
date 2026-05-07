# -*- coding: utf-8 -*-
from astronex.compat import Gtk, Gdk, GObject, cairo, pango, pangocairo
import math
from .. drawing.dispatcher import DrawMixin
from .. gui.plselector_dlg import PlanSelector
from .. gui.popup import PlanPopup, TextPopup
from .. gui.cycle_dlg import CycleSelector
from .. gui.aux_dlg import AuxWindow
from .. gui.bridgewin import BridgePEWindow
from path import Path
from .. countries import cata_reg
from .. utils import parsestrtime
from .sdasurface import DrawDiagram, HouseSelector
from datetime import datetime, timedelta
from .. boss import boss
curr = boss.get_state()

MAGICK_COL = 65535.0
initmenu = (_('Ayuda'),_('Acercar'),_('Solo EA'),_('Ver zonas PE'),
        _('Ver zonas de casa'),_('Ver EA'),_('Activar goodwill'),
        _('Ocultar unilaterales'),_('Ego-clics'),_('Ver todos los aspectos'))
bios = ['bio_nat','bio_nod','bio_soul','bio_dharma']
peops = ['draw_nat','draw_nod','draw_soul','draw_local']
sheetops = ['dat_nat', 'dat_nod', 'dat_house', 'prog_nat', 'prog_nod', 'prog_local', 'prog_soul' ]
extended = ['prog_nat','prog_nod','prog_soul','prog_local','compo_one','compo_two']

class DrawMaster(Gtk.Layout):
    fullscreen = False
    panning = False
    zoom_in = False
    panelvisible = False
    diadavisible = False
    hselvisible = False
    pepending = [False,None,None]
    rulinepending = None
    bridge = None
    sec_alltimes = False
    overlay = False

    def __init__(self,boss):
        self.boss = boss
        self.opts = boss.opts
        Gtk.Layout.__init__(self)
        self.menu = Gtk.Menu()
        self.hidden_op = {}
        for buf in initmenu:
            menu_item = Gtk.MenuItem(label=buf)
            self.menu.append(menu_item)
            menu_item.connect("activate", self.on_menuitem_activate)
            if buf in [_('Ayuda'),_('Ver EA')]:
                sep_item = Gtk.SeparatorMenuItem()
                self.menu.append(sep_item)
                sep_item.show()
            if buf not in [_('Ver EA'),_('Ver zonas PE'),_('Ver zonas de casa'),
                    _('Ver todos los aspectos'),_('Ego-clics')]:
                menu_item.show()
            elif buf == _('Ver EA'):
                self.hidden_op['ea'] = menu_item
            elif buf == _('Ver zonas PE'):
                self.hidden_op['pez'] = menu_item
            elif buf == _('Ver zonas de casa'):
                self.hidden_op['hz'] = menu_item
            elif buf == _('Ver todos los aspectos'):
                self.hidden_op['acl'] = menu_item
            elif buf == _('Ego-clics'):
                self.hidden_op['ego'] = menu_item

        self.set_events(Gdk.EventMask.BUTTON_PRESS_MASK |
                Gdk.EventMask.BUTTON_RELEASE_MASK |
                Gdk.EventMask.POINTER_MOTION_MASK |
                Gdk.EventMask.POINTER_MOTION_HINT_MASK |
                Gdk.EventMask.SCROLL_MASK)
        self.connect("draw",self.dispatch)
        self.connect("button_press_event", self.on_da_clicked)
        self.connect("button_release_event", self.on_da_clicked)
        self.connect("motion_notify_event", self.on_da_clicked)
        self.connect("scroll-event", self.on_scroll)
        self.panel = ChangeDatePanel(self)
        self.put(self.panel,-200,-200)

        self.create_special_area()
        self.create_hselector()
        self.drawer = DrawMixin(boss.opts,self)
        self.plselector = None
        self.cycleselector = None
        self.planpopup = None
        self.textspopup = None
        self.where_diada = 0
        self.where_hsel = 0
        self.auxwins = []

        self.ha = self.get_hadjustment()
        self.va = self.get_vadjustment()
        self.m_x = 0
        self.m_y = 0

    def create_special_area(self):
        frame = Gtk.Frame()
        diada = DrawDiagram(self.boss)
        diada.set_size_request(275,275)
        frame.add(diada)
        self.put(frame,-280,0)
        self.diada = frame

    def create_hselector(self):
        frame = Gtk.Frame()
        hsel = HouseSelector(self.boss)
        hsel.set_size_request(120,120)
        frame.add(hsel)
        self.put(frame,-160,612)
        self.hsel = frame

    def on_da_clicked(self,da,event):
        showAP = DrawMixin.get_showAP()
        x, y = event.x,event.y
        info = self.move_info
        if event.type == Gdk.EventType.BUTTON_PRESS and event.button == 3:
            self.menu.popup(None, None, None, None, event.button, event.time)
            return True
        if event.type == Gdk.EventType.DOUBLE_BUTTON_PRESS and event.button == 1:
            if showAP or curr.curr_chart == curr.now or curr.curr_op in ['draw_transits','rad_and_transit']:
                self.panel.nowbut.emit('clicked')
                info['button'] = 100; #now
                if self.cycleselector:
                    cycles = curr.curr_chart.get_cycles()
                    self.cycleselector.adj.set_value(cycles+1)
            elif curr.curr_op == 'sec_prog':
                self.sec_alltimes = not(self.sec_alltimes)
            return True
        elif event.type == Gdk.EventType.BUTTON_PRESS and event.button == 1:
            if curr.curr_op in bios and curr.opmode == 'simple':
                return False
            if event.button != 1: return False
            if info['button'] < 0:
                info['button'] = event.button
                if self.panning:
                    fleur = Gdk.Cursor.new_for_display(Gdk.Display.get_default(), Gdk.CursorType.FLEUR)
                    Gdk.Device.grab(event.device, self.get_bin_window(), Gdk.GrabOwnership.APPLICATION, True,
                            Gdk.EventMask.POINTER_MOTION_MASK | Gdk.EventMask.BUTTON_RELEASE_MASK |
                            Gdk.EventMask.POINTER_MOTION_HINT_MASK, fleur, event.time)
                    info['click_x'] = event.x
                    info['click_y'] = event.y
            elif info['button'] == 100:
                info['button'] = -1
            if showAP is None:
                return True
            w = da.get_allocated_width()/2; h = da.get_allocated_height()/2
            if curr.opmode == 'simple' and curr.curr_op in peops:
                pass
            elif curr.opmode == 'double' or curr.curr_op == 'rad_and_transit':
                deg = math.degrees(math.atan2(y-h, (x%w)-(w/2) ))
                for_op = [curr.opleft,curr.opright][x > w]
                if curr.clickmode == 'click':
                    for_ch = ['chart','click'][x > w]
                else:
                    for_ch = 'chart'
                if deg == 0.0: deg = 0.0001
                self.drawer.set_AP(deg,for_op,for_ch)
                self.redraw()
                dt = curr.date.dt
                dt = datetime.combine(dt.date(),dt.time())
                self.hsel.get_child().set_house_from_date(dt)
                self.redraw_auxwins()
                info['button'] = -1
            else:
                return False
            return True
        elif event.type == Gdk.EventType.BUTTON_PRESS and event.button == 2:
            if curr.clickmode == 'click' and curr.opmode != 'simple':
                return
            if curr.opmode == 'double':
                boss.mpanel.chooser.swap_ops()
                boss.da.redraw_auxwins(True)
            elif curr.opmode == 'triple':
                x, y = event.x,event.y
                w, h = da.get_allocated_width(), da.get_allocated_height()
                side = ['up',None][y > (h/2)]
                if not side:
                    side = ['left','right'][x > (w/2)]
                boss.mpanel.chooser.swap_ops(side)
            elif curr.opmode == 'simple':
                if self.zoom_in:
                    self.panning = not self.panning
                elif not showAP:
                    nb = boss.mpanel.chooser.notebook
                    page = nb.get_current_page()
                    sel = nb.get_nth_page(page).get_selection()
                    m,i = sel.get_selected()
                    ix = m.get_path(i)[0]
                    if ix == 0 and not self.planpopup:
                        self.planpopup = PlanPopup(boss)
                    elif page == 3 and ix in [2,3,4]:
                        if not self.textspopup:
                            self.textspopup = TextPopup(ix)
                else:
                    self.drawer.set_op_AP(curr.curr_op,event.state )
                    dt = curr.date.dt
                    dt = datetime.combine(dt.date(),dt.time())
                    self.hsel.get_child().set_house_from_date(dt)
                    self.redraw()
                    self.redraw_auxwins()
        elif event.type == Gdk.EventType.BUTTON_RELEASE:
            if self.planpopup:
                self.planpopup.destroy()
                self.planpopup = None
            if curr.curr_op in bios or curr.opmode != 'simple':
                return False
            if info['button'] < 0 or info['button'] == 100:
                return True
            if info['button'] == event.button:
                info['button'] = -1;
                if self.panning:
                    Gdk.Device.ungrab(event.device, event.time)
                else:
                    self.drawer.ruline = None
                    self.rulinepending = None
                    if showAP:
                        w = da.get_allocated_width()/2; h = da.get_allocated_height()/2
                        deg = math.degrees(math.atan2(y-h,x-w))
                        for_op = curr.curr_op
                        for_ch = 'chart'
                        self.drawer.set_AP(deg,for_op,for_ch)
                        dt = curr.date.dt
                        dt = datetime.combine(dt.date(),dt.time())
                        self.hsel.get_child().set_house_from_date(dt)
                    self.redraw()
                    boss.redraw(both=False)
                    self.redraw_auxwins()
        elif Gdk.EventType.MOTION_NOTIFY:
            if curr.curr_op in bios or curr.opmode != 'simple':
                return False
            x, y = event.x, event.y
            if DrawMaster.overlay:
                self.m_x = x
                self.m_y = y
                self.queue_draw()
            if info['button'] < 0 or info['button'] == 100:
                info['button'] = -1
                return False
            w = da.get_allocated_width()/2; h = da.get_allocated_height()/2
            if self.panning:
                x_off = info['click_x'] - x
                y_off = info['click_y'] - y
                w_all = self.get_allocated_width()
                h_all = self.get_allocated_height()
                wrange = w_all - self.ha.get_page_size()
                hrange = h_all - self.va.get_page_size()
                if x_off + self.ha.get_value() < 0:
                    self.ha.set_value(0)
                elif x_off + self.ha.get_value() > wrange:
                    self.ha.set_value(wrange)
                else:
                    self.ha.set_value(self.ha.get_value() + x_off)
                if y_off + self.va.get_value() < 0:
                    self.va.set_value(0)
                elif y_off + self.va.get_value() > hrange:
                    self.va.set_value(hrange)
                else:
                    self.va.set_value(self.va.get_value() + y_off)
            else:
                self.drawer.ruline = (x-w,y-h)
                self.queue_draw()

    def toggle_overlay(self):
        DrawMaster.overlay = not DrawMaster.overlay
        if DrawMaster.overlay:
            cursor = Gdk.Cursor.new_for_display(Gdk.Display.get_default(), Gdk.CursorType.BLANK_CURSOR)
            self.get_window().set_cursor(cursor)
        else:
            self.get_window().set_cursor(None)
        self.queue_draw()

    def on_scroll(self,da,event):
        x, y = event.x,event.y
        w, h = da.get_allocated_width(), da.get_allocated_height()
        side = None

        if event.direction == Gdk.ScrollDirection.UP:
            delta = -1
        else:
            delta = 1

        if self.textspopup:
            self.textspopup.destroy()
            self.textspopup = None
            nb = boss.mpanel.chooser.notebook
            page = nb.get_current_page()
            m,i = nb.get_nth_page(page).get_selection().get_selected()
            ix = m.get_path(i)[0] + delta
            if page == 3 and ix in [2,3,4]:
                self.textspopup = TextPopup(ix)

        if  curr.opmode == 'simple':
            boss.mpanel.chooser.delta_select(delta)
        elif  curr.opmode == 'triple':
            side = ['up',None][y > (h/2)]
            if not side:
                side = ['left','right'][x > (w/2)]
            curr.set_opdelta(delta,side)
            boss.mpanel.chooser.delta_triple_select(delta,side)
        elif  curr.opmode == 'double':
            side = ['left','right'][x > (w/2)]
            curr.set_opdelta(delta,side)
            boss.mpanel.chooser.delta_double_select(delta,side)

        self.redraw()
        return True

    def on_menuitem_activate(self,menuitem):
        if menuitem.get_child().get_text() == _('Acercar'):
            scrw, scrh = self.get_size_request()
            self.set_size_request(scrw*2,scrh*2)
            self.zoom_in = True
            self.panning = True
            menuitem.get_child().set_text(_('Alejar'))
        elif menuitem.get_child().get_text() == _('Alejar'):
            scrw, scrh = self.get_size_request()
            self.set_size_request(scrw/2,scrh/2)
            self.zoom_in = False
            self.panning = False
            menuitem.get_child().set_text(_('Acercar'))
        elif menuitem.get_child().get_text() == _('Ayuda'):
            boss.mainwin.show_help()
        elif menuitem.get_child().get_text() == _('Ver zonas PE'):
            self.drawer.pe_zones = True
            self.redraw_auxwins(True)
            menuitem.get_child().set_text(_('Ocultar zonas PE'))
        elif menuitem.get_child().get_text() == _('Ocultar zonas PE'):
            self.drawer.pe_zones = False
            self.redraw_auxwins(True)
            menuitem.get_child().set_text(_('Ver zonas PE'))
        elif menuitem.get_child().get_text() == _('Ver zonas de casa'):
            self.drawer.hzones = True
            menuitem.get_child().set_text(_('Ocultar zonas de casa'))
        elif menuitem.get_child().get_text() == _('Ocultar zonas de casa'):
            self.drawer.hzones = False
            menuitem.get_child().set_text(_('Ver zonas de casa'))
        elif menuitem.get_child().get_text() == _('Solo EA'):
            DrawMixin.set_onlyEA(True)
            menuitem.get_child().set_text(_('Mostrar todo'))
        elif menuitem.get_child().get_text() == _('Mostrar todo'):
            DrawMixin.set_onlyEA(False)
            menuitem.get_child().set_text(_('Solo EA'))
        elif menuitem.get_child().get_text() == _('Activar goodwill'):
            self.drawer.goodwill = True
            menuitem.get_child().set_text(_('Desactivar goodwill'))
        elif menuitem.get_child().get_text() == _('Desactivar goodwill'):
            self.drawer.goodwill = False
            menuitem.get_child().set_text(_('Activar goodwill'))
        elif menuitem.get_child().get_text() == _('Ocultar unilaterales'):
            self.drawer.uniaspect = False
            menuitem.get_child().set_text(_('Mostrar unilaterales'))
        elif menuitem.get_child().get_text() == _('Mostrar unilaterales'):
            self.drawer.uniaspect = True
            menuitem.get_child().set_text(_('Ocultar unilaterales'))
        elif menuitem.get_child().get_text() == _('Ver EA'):
            DrawMixin.set_showEA(True)
            menuitem.get_child().set_text(_('Ocultar EA'))
        elif menuitem.get_child().get_text() == _('Ocultar EA'):
            DrawMixin.set_showEA(False)
            menuitem.get_child().set_text(_('Ver EA'))
        elif menuitem.get_child().get_text() == _('Ver todos los aspectos'):
            self.drawer.allclick = True
            menuitem.get_child().set_text(_('Ver solo clics'))
        elif menuitem.get_child().get_text() == _('Ver solo clics'):
            self.drawer.allclick = False
            menuitem.get_child().set_text(_('Ver todos los aspectos'))
        elif menuitem.get_child().get_text() == _('Ego-clics'):
            self.drawer.egoclick = True
            menuitem.get_child().set_text(_('Clics sin ego'))
        elif menuitem.get_child().get_text() == _('Clics sin ego'):
            self.drawer.egoclick = False
            menuitem.get_child().set_text(_('Ego-clics'))

        self.redraw()

    def toggle_menulist(self,men,dothing):
        if dothing == 'add':
            self.hidden_op[men].show()
        elif dothing == 'remove':
            self.hidden_op[men].hide()

    def popup_menu(self):
        self.menu.popup(None, None, None, None, 1, Gtk.get_current_event_time())

    def redraw(self):
        w = int(self.ha.get_upper() - self.ha.get_lower())
        h = int(self.va.get_upper() - self.va.get_lower())
        x = int(self.ha.get_lower())
        y = int(self.va.get_lower())
        self.get_bin_window().invalidate_rect(Gdk.Rectangle(x=x,y=y,width=w,height=h),False)
        if self.diadavisible:
            w = self.diada.get_child().get_allocated_width()
            h = self.diada.get_child().get_allocated_height()
            self.diada.get_child().get_window().invalidate_rect(Gdk.Rectangle(x=0,y=0,width=w,height=h),False)
        if boss.da.hselvisible:
            boss.da.hsel.get_child().queue_draw()

    def redraw_auxwins(self,onlybridge=False):
        if self.bridge:
            self.bridge.sda.redraw()
        if onlybridge:
            return
        for aux in self.auxwins:
            aux.sda.redraw()

    def show_panel(self,menuitem=None):
        self.move(self.panel,0,0)
        self.panelvisible = True

    def hide_panel(self,menuitem=None):
        self.move(self.panel,-200,-200)
        self.panelvisible = False
        if curr.curr_chart == curr.now:
            self.panel.nowbut.emit('clicked')

    def show_pe(self,menuitem=None):
        if curr.curr_chart == curr.now:
            boss.mpanel.toolbar.get_nth_item(1).set_active(False)
            return
        DrawMixin.set_showAP('now')
        self.redraw()
        self.redraw_auxwins()

    def hide_pe(self,menuitem=None):
        DrawMixin.set_showAP(None)
        self.redraw()
        self.redraw_auxwins()

    def show_diada(self,menuitem=None):
        where = self.get_allocated_width() - self.diada.get_allocated_width()
        self.move(self.diada,where,0)
        self.diadavisible = True
        self.redraw()

    def hide_diada(self,menuitem=None):
        self.move(self.diada,-280,0)
        self.diadavisible = False
        self.redraw()

    def make_auxwin(self):
        self.auxwins.append(AuxWindow(boss.mainwin))
        sda = self.auxwins[-1].sda
        sda.drawer.hoff = sda.get_allocated_width() * 0.125
        sda.drawer.gridw = sda.drawer.hoff * 6

    def make_pebridge(self):
        if not self.bridge:
            self.bridge = BridgePEWindow(boss.mainwin)

    def hide_pebridge(self):
        self.bridge.exit()
        self.bridge = None


    def make_plsel(self):
        if not self.plselector:
            self.plselector = PlanSelector(self.boss.mainwin)
            self.plselector.move(0,0)

    def make_cycleswin(self):
        if not self.cycleselector:
            self.cycleselector = CycleSelector(self.boss.mainwin)
            wx,wy = self.boss.mainwin.get_position()
            ww,wh =self.boss.mainwin.get_size()
            w,h= self.cycleselector.get_allocated_width(), self.cycleselector.get_allocated_height()
            self.cycleselector.move(wx+ww-w-10,wh+wy-h-24)

    def dispatch(self,da,cr):
        if self.diadavisible:
            where = self.get_allocated_width() - self.diada.get_allocated_width()
            if self.where_diada != where:
                self.move(self.diada,where,0)
                self.where_diada = where

        op = curr.curr_op
        if self.fullscreen:
            DrawMixin.extended_canvas = False
        elif op in extended and curr.opmode == 'simple' :
            if not DrawMixin.extended_canvas:
                DrawMixin.extended_canvas = True
                pad = 160;
                if op in ['compo_one','compo_two']:
                    if boss.mainwin.scr_width <= 1024:
                        pad = self.get_allocated_width() * 0.4
                    else:
                        pad = self.get_allocated_width() * 0.55
                self.set_size_request(720,int(720+pad))
        else:
            if DrawMixin.extended_canvas:
                DrawMixin.extended_canvas = False
                self.set_size_request(720,720)

        if op in bios and not self.hselvisible and curr.opmode == 'simple':
            where = self.get_allocated_height() - self.hsel.get_allocated_height()
            self.move(self.hsel,0,where)
            self.hselvisible = True
        elif self.hselvisible and (curr.opmode != 'simple' or op not in bios):
            self.move(self.hsel,-160,650)
            self.hselvisible = False

        if self.hselvisible:
            where = self.get_allocated_height() - self.hsel.get_allocated_height()
            if self.where_hsel != where:
                self.move(self.hsel,0,where)
                self.where_hsel = where

        w = self.get_allocated_width()
        h = self.get_allocated_height()
        cr.rectangle(0,0,w,h)
        cr.clip()
        cr.set_source_rgb(1.0,1.0,1.0)
        cr.rectangle(0,0,w,h)
        cr.fill()
        cr.set_line_join(cairo.LINE_JOIN_ROUND)
        cr.set_line_width(float(self.opts.base))

        if self.diadavisible:
            cr.translate(0,h*0.15)
            w *= 0.85; h *= 0.85
        self.drawer.dispatch_pres(cr,w,h)
        if self.diadavisible:
            w /= 0.85; h /= 0.85

        cr.identity_matrix()
        if self.pepending[0]:
            self.draw_pelabel(cr,w,h)
            self.pepending = [False,None,None]
        elif curr.curr_chart == curr.now or curr.curr_op in ['draw_transits','solar_rev']:
            self.d_now_date(cr,w,h)
        if self.rulinepending:
            self.d_ruldegree(cr,w,h)
        self.draw_label(cr,w,h)
        if self.check_local_label():
            self.d_loclbl(cr,w,h)

        if DrawMaster.overlay:
            col = Gdk.color_parse('#'+self.opts.overlay)
            ovcol = [col.red/MAGICK_COL,col.green/MAGICK_COL,col.blue/MAGICK_COL,0.5]
            cr.set_source_rgba(*ovcol)
            radial = cairo.RadialGradient(self.m_x,self.m_y,45,self.m_x,self.m_y,50)
            radial.add_color_stop_rgba(0.0,0,0,1,0)
            radial.add_color_stop_rgba(0.9,1,0,0,1)
            cr.mask(radial)
        return True

    def check_local_label(self):
        if curr.opmode == 'simple' and curr.curr_op == 'draw_local':
            return True
        labelyes = curr.opleft == 'draw_local' or curr.opright == 'draw_local'
        if curr.opmode == 'double' and labelyes:
            return True
        if curr.opmode == 'triple' and (labelyes or curr.opup == 'draw_local'):
            return True
        return False

    def d_ruldegree(self,cr,w,h):
        if self.diadavisible:
            return
        sign,deg = divmod(self.rulinepending,30)
        mint = int((deg - int(deg)) * 60)
        sign = int(sign)
        deg = int(deg)
        let = self.drawer.zodlet[sign]
        col = boss.opts.zodiac.zod[sign].col
        signs = "%s\u00b0 %s\u00b4" % (deg,mint)
        layout = pangocairo.create_layout(cr)
        cr.set_source_rgb(0,0,0.6)
        font = pango.FontDescription(self.opts.font)
        font.set_size(9*pango.SCALE)
        layout.set_font_description(font)
        layout.set_text(signs, -1)
        ink,logical = layout.get_extents()
        xpos = logical.width/pango.SCALE
        cr.move_to(w-xpos-20,20)
        pangocairo.show_layout(cr, layout)

        font = pango.FontDescription("Astro-Nex")
        font.set_size(9*pango.SCALE)
        layout.set_font_description(font)
        cr.set_source_rgb(*col)
        layout.set_text(let, -1)
        ink,logical = layout.get_extents()
        xpos = logical.width/pango.SCALE
        cr.move_to(w-xpos-5,20)
        pangocairo.show_layout(cr, layout)

    def draw_pelabel(self,cr,w,h):
        if self.diadavisible:
            return

        date = curr.date.ld
        date_str = date.__str__().split(' ')[0].split('-')
        date_str.reverse()
        date_str = "/".join(date_str)
        layout = pangocairo.create_layout(cr)

        signs = ['','']
        collet = [None,None]
        for i in [1,2]:
            pe = self.pepending[i]
            if not pe: break
            sign,deg = divmod(pe,30)
            mint = int((deg - int(deg)) * 60)
            sign = int(sign)
            deg = int(deg)
            let = self.drawer.zodlet[sign]
            col = boss.opts.zodiac.zod[sign].col
            collet[i-1] = (col,let,i%2)
            signs[i-1] = "%s\u00b0 %s\u00b4" % (deg,mint)
        if signs[1]:
            signs[0],signs[1] = signs[1],signs[0]

        cr.set_source_rgb(0,0,0.6)
        font = pango.FontDescription(self.opts.font)
        font.set_size(9*pango.SCALE)
        layout.set_font_description(font)
        layout.set_text(signs[1]+" "+date_str+" "+signs[0], -1)
        ink,logical = layout.get_extents()
        xpos = logical.width/pango.SCALE
        cr.move_to(w-xpos-20,5)
        pangocairo.show_layout(cr, layout)

        font = pango.FontDescription("Astro-Nex")
        font.set_size(9*pango.SCALE)
        layout.set_font_description(font)
        if collet[1]:
            off = xpos+22
            for col,let,f in collet:
                cr.set_source_rgb(*col)
                layout.set_text(let, -1)
                ink,logical = layout.get_extents()
                xpos = logical.width/pango.SCALE
                cr.move_to(w-xpos-5-f*off,5)
                pangocairo.show_layout(cr, layout)
        else:
            col,let,f = collet[0]
            cr.set_source_rgb(*col)
            layout.set_text(let, -1)
            ink,logical = layout.get_extents()
            xpos = logical.width/pango.SCALE
            cr.move_to(w-xpos-5,5)
            pangocairo.show_layout(cr, layout)

    def d_now_date(self,cr,w,h):
        #import pangocairo
        if self.diadavisible:
            return
        strdate = curr.charts['now'].date
        date,time = parsestrtime(strdate)
        date = date + " " + time.split(" ")[0]
        layout = pangocairo.create_layout(cr)
        cr.set_source_rgb(0,0,0.6)
        font = pango.FontDescription(self.opts.font)
        font.set_size(9*pango.SCALE)
        layout.set_font_description(font)
        layout.set_text(date, -1)
        ink,logical = layout.get_extents()
        xpos = logical.width/pango.SCALE
        cr.move_to(w-xpos-18,5)
        pangocairo.show_layout(cr, layout)

        font = pango.FontDescription("Astro-Nex")
        font.set_size(9*pango.SCALE)
        layout.set_font_description(font)
        regent = curr.year_regent()
        pl = boss.opts.zodiac.plan[regent]
        cr.set_source_rgb(*pl.col)
        layout.set_text(pl.let, -1)
        ink,logical = layout.get_extents()
        xpos = logical.width/pango.SCALE
        cr.move_to(w-xpos-5,5)
        pangocairo.show_layout(cr, layout)


    def d_loclbl(self,cr,w,h):
        #import pangocairo
        layout = pangocairo.create_layout(cr)
        cr.set_source_rgb(0,0.5,0.3)
        font = pango.FontDescription(self.opts.font)
        font.set_size(8*pango.SCALE)
        layout.set_font_description(font)
        region = curr.loc.region
        if boss.opts.lang == 'ca' and curr.loc.country == 'España':
            region = cata_reg[region]
        layout.set_text(curr.loc.city+' ('+region+'-'+t(curr.loc.country)[0]+')', -1)
        ink,logical = layout.get_extents()
        xpos = logical.width/pango.SCALE
        cr.move_to(w/2-xpos/2,h-15)
        pangocairo.show_layout(cr, layout)

    def draw_label(self,cr,w,h):
        #import pangocairo
        if curr.curr_op in sheetops:
            return
        layout = pangocairo.create_layout(cr)
        font = pango.FontDescription(self.opts.font)
        font.set_size(9*pango.SCALE)
        layout.set_font_description(font)
        h -= 20 if self.fullscreen else 15

        cols = [(0,0,0.4),(0.8,0,0.1)]
        ix = [0,1][curr.clickmode == 'click']
        charts = (curr.curr_chart,curr.curr_click)
        for i in range(ix+1):
            name = "%s %s" % (charts[i].first,charts[i].last)
            layout.set_text(name, -1)
            ink,logical = layout.get_extents()
            xpos = logical.width/pango.SCALE
            if ix and not i:
                pos = 0 + 5
            else:
                pos = w - xpos - 5
            cr.set_source_rgb(*cols[i])
            cr.move_to(pos,h)
            pangocairo.show_layout(cr, layout)
        if self.diadavisible and curr.clickmode == 'click':
            where = self.get_allocated_width() - self.diada.get_allocated_width()
            name = "%s %s" % (charts[0].first,charts[0].last)
            layout.set_text(name, -1)
            ink,logical = layout.get_extents()
            xpos = logical.width/pango.SCALE
            cr.move_to(where-20,5+xpos)
            cr.rotate(-90*math.pi/180)
            cr.set_source_rgb(*cols[0])
            pangocairo.show_layout(cr, layout)


############################################
############################################

class ChangeDatePanel(Gtk.VBox):
    changes = ['minutes','hours','days']
    def __init__(self,parent):
        Gtk.VBox.__init__(self)

        frame = Gtk.Frame()
        self.time = curr.date.ld.time()
        self.internal_signal = True
        self.needsredrawing = True
        self.calendar = Gtk.Calendar()
        self.calendar.set_display_options(Gtk.CalendarDisplayOptions.SHOW_HEADING)
        self.calendar.connect('day-selected', self.on_calendar_day_selected,parent)
        self.mth_hid = self.calendar.connect('month-changed',self.on_calendar_day_selected,parent)
        frame.add(self.calendar)
        self.pack_start(frame, False, False, 0)

        self.set_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        self.connect("button_press_event", lambda s,but: True)

        butbox = Gtk.HBox()

        adj = Gtk.Adjustment(value=1,lower=1,upper=10,step_increment=1,page_increment=5)
        self.spin = Gtk.SpinButton(adjustment=adj)
        self.spin.set_wrap(True)
        self.spin.set_alignment(1.0)
        self.spin.set_size_request(40,-1)
        butbox.pack_start(self.spin,False,False,0)

        button = Gtk.Button()
        button.set_events(Gdk.EventMask.BUTTON_PRESS_MASK|Gdk.EventMask.BUTTON_RELEASE_MASK)
        arrow = Gtk.Arrow(arrow_type=Gtk.ArrowType.LEFT, shadow_type=Gtk.ShadowType.NONE)
        button.add(arrow)
        button.dir = '<'
        button.connect("button_press_event",self.on_panel_clicked,parent)
        button.connect("button_release_event",self.on_panel_clicked,parent)
        butbox.pack_start(button,False,False,0)

        self.combo = Gtk.ComboBoxText()
        self.combo.append_text(_("minutos"))
        self.combo.append_text(_("horas"))
        self.combo.append_text(_("dias"))
        self.combo.set_active(2)
        self.combo.set_size_request(70,-1)
        butbox.pack_start(self.combo,False,False,0)

        button = Gtk.Button()
        button.set_events(Gdk.EventMask.BUTTON_PRESS_MASK|Gdk.EventMask.BUTTON_RELEASE_MASK)
        arrow = Gtk.Arrow(arrow_type=Gtk.ArrowType.RIGHT, shadow_type=Gtk.ShadowType.NONE)
        button.add(arrow)
        button.dir = '>'
        button.connect("button_press_event",self.on_panel_clicked,parent)
        button.connect("button_release_event",self.on_panel_clicked,parent)
        butbox.pack_start(button,False,False,0)

        but = Gtk.Button()
        img = Gtk.Image()
        appath = boss.app.appath
        imgfile = Path.joinpath(appath,"astronex/resources/refresh-18.png")
        img.set_from_file(str(imgfile))
        but.set_image(img)
        butbox.pack_start(but,False,False,0)
        but.connect('clicked',self.on_now_clicked)
        self.nowbut = but
        self.pack_start(butbox,False,False,0)

    def on_calendar_day_selected(self,cal,parent):
        y,m,d = cal.get_date()
        time = self.time
        try:
            date = datetime.combine(datetime(y,m+1,d),time)
        except ValueError:
            try:
                date = datetime.combine(datetime(y,m+1,d-1),time)
            except ValueError:
                date = datetime.combine(datetime(y,m+1,d-3),time)
        curr.date.setdt(date)
        curr.refresh_nowchart()
        boss.mpanel.act_now(curr.now)
        if parent.cycleselector:
            cycles = curr.curr_chart.get_cycles(date)
            parent.cycleselector.adj.set_value(cycles+1)
        if self.internal_signal:
            boss.da.hsel.get_child().set_house_from_date(date)
        if self.needsredrawing:
            parent.redraw()
            parent.redraw_auxwins()
        else:
            self.needsredrawing = True
        self.internal_signal = True

    def on_panel_clicked(self,but,event,parent):
        delta = self.spin.get_value_as_int()
        if but.dir == '<':
            delta = -delta
        change = self.changes[self.combo.get_active()]
        if event.type == Gdk.EventType.BUTTON_PRESS:
            self.timeout_sid = GObject.timeout_add(80,self.start_spining,delta,change)
        elif event.type == Gdk.EventType.BUTTON_RELEASE:
            GObject.source_remove(self.timeout_sid)

    def start_spining(self,delta,change):
        dt = self.set_delta((delta,change))
        self.set_date(dt,True)
        return True

    def on_now_clicked(self,but):
        self.set_date(datetime.now(),True)

    def update_cycles(self,delta):
        y,m,d = self.calendar.get_date()
        y = y + 72*delta
        self.set_date(datetime(y,m+1,d))

    def set_date(self,date,timechanged=False):
        if timechanged:
            self.time = date.time()
            self.internal_signal = True
        else:
            self.time = curr.date.ld.time()
            self.internal_signal = False
        self.set_cal(date)

    def set_cal(self,date):
        self.calendar.handler_block(self.mth_hid)
        self.calendar.select_month(date.month - 1, date.year)
        self.calendar.handler_unblock(self.mth_hid)
        self.calendar.select_day(date.day)
        self.calendar.clear_marks()
        self.calendar.mark_day(date.day)

    def set_date_only(self,date):
        self.time = date.time()
        self.internal_signal = True
        self.set_cal(date)
        self.needsredrawing = False

    def set_delta(self,delta):
        amount = delta[0]
        what = delta[1]
        dt = datetime.combine(curr.date.ld.date(),curr.date.ld.time())
        if what == 'minutes':
            dt = dt + timedelta(minutes=amount)
        elif what == 'hours':
            dt = dt + timedelta(hours=amount)
        elif what == 'days':
            dt = dt + timedelta(days=amount)
        return dt

