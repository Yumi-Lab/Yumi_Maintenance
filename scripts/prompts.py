import logging
import os
from io import BytesIO
import qrcode
from PIL import Image
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GdkPixbuf


def generate_qrcode_pixbuf(url):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=6,
        border=2,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="grey", back_color="black")

    buffer = BytesIO()
    try:
        img.save(buffer, format='PNG')
    except Exception:
        img.save(buffer)

    buffer.seek(0)
    loader = GdkPixbuf.PixbufLoader.new_with_type('png')
    loader.write(buffer.read())
    loader.close()
    return loader.get_pixbuf()


class Prompt:
    def __init__(self, screen):
        self.screen = screen
        self.gtk = screen.gtk
        self.window_title = _('KlipperScreen')  # Seul texte codé en dur (titre par défaut)
        self.text = self.header = ""
        self.buttons = []
        self.id = 1
        self.prompt = None
        self.scroll_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.groups = []

        self.image_path = None
        self.qrcode_url = None

        self._init_css()

    def _init_css(self):
        css = b"""
        #prompt-title {
            font-size: 30px;
            font-weight: bold;
            color: white;
        }
        #prompt-text {
            font-size: 22px;
            color: white;
        }
        .visual-frame {
            margin: 15px 25px 15px 15px;
            padding: 8px;
            background-color: black;
            border-radius: 5px;
        }
        .content-box {
            margin: 10px;
        }
        """
        style_provider = Gtk.CssProvider()
        style_provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            style_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def _key_press_event(self, widget, event):
        keyval_name = Gdk.keyval_name(event.keyval)
        if keyval_name in ["Escape", "BackSpace"]:
            self.close()

    def decode(self, data):
        logging.info(f'{data}')
        if data.startswith('prompt_begin'):
            # Récupère le texte brut depuis la macro
            raw_header = data.replace('prompt_begin', '').strip()
            # Applique la traduction au texte dynamique
            self.header = _(raw_header) if raw_header else ""
            self.window_title = self.header
            self.text = ""
            self.buttons = []
            self.image_path = None
            self.qrcode_url = None
            return
        elif data.startswith('prompt_text'):
            # Récupère le texte brut depuis la macro
            raw_text = data.replace('prompt_text ', '')
            # Applique la traduction au texte dynamique
            self.text += _(raw_text) + "\n" if raw_text else ""
            return
        elif data.startswith('prompt_image '):
            self.image_path = data.replace('prompt_image ', '').strip()
            return
        elif data.startswith('prompt_qrcode '):
            self.qrcode_url = data.replace('prompt_qrcode ', '').strip()
            return
        elif data.startswith('prompt_button '):
            data = data.replace('prompt_button ', '')
            params = data.split('|')
            if len(params) == 1:
                params.append(self.text)
            if len(params) > 3:
                logging.error('Unexpected number of parameters on the button')
                return
            
            # Traduction du nom du bouton dynamique
            params[0] = _(params[0]) if params[0] else params[0]
            self.set_button(*params)
            return
        elif data.startswith('prompt_footer_button '):
            data = data.replace('prompt_footer_button ', '')
            params = data.split('|')
            if len(params) == 1:
                params.append(self.text)
            if len(params) > 3:
                logging.error('Unexpected number of parameters on the button')
                return
            
            # Traduction du nom du bouton dynamique
            params[0] = _(params[0]) if params[0] else params[0]
            self.set_footer_button(*params)
            return
        elif data == 'prompt_show':
            if not self.prompt:
                self.show()
            return
        elif data == 'prompt_end':
            self.end()
        elif data == 'prompt_button_group_start':
            self.groups.append(Gtk.FlowBox(
                selection_mode=Gtk.SelectionMode.NONE,
                orientation=Gtk.Orientation.HORIZONTAL,
            ))
        elif data == 'prompt_button_group_end':
            if self.groups:
                self.scroll_box.add(self.groups.pop())
        else:
            logging.debug(f'Unknown option {data}')

    def set_button(self, name, gcode, style='default'):
        button = self.gtk.Button(image_name=None, label=name, style=f'dialog-{style}')
        button.connect("clicked", self.screen._send_action, "printer.gcode.script", {'script': gcode})
        if self.groups:
            self.groups[-1].add(button)
            max_childs = len(self.groups[-1].get_children())
            self.groups[-1].set_max_children_per_line(min(4, max_childs))
            self.groups[-1].set_min_children_per_line(min(4, max_childs))
        else:
            self.scroll_box.add(button)

    def set_footer_button(self, name, gcode, style='default'):
        self.buttons.append(
            {"name": name, "response": self.id, 'gcode': gcode, 'style': f'dialog-{style}'}
        )
        self.id += 1

    def show(self):
        logging.info(f'Prompt {self.header} {self.text} {self.buttons}')

        title = Gtk.Label(label=self.header, wrap=True)
        title.set_name("prompt-title")
        title.set_halign(Gtk.Align.CENTER)
        title.set_hexpand(True)

        close = self.gtk.Button("cancel", scale=self.gtk.bsidescale)
        close.set_hexpand(False)
        close.set_vexpand(False)
        close.connect("clicked", self.close)

        visual_elements = []
        
        try:
            if self.image_path and os.path.isfile(self.image_path):
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(self.image_path, 200, 200, True)
                visual_elements.append(Gtk.Image.new_from_pixbuf(pixbuf))
            if self.qrcode_url:
                pixbuf = generate_qrcode_pixbuf(self.qrcode_url)
                pixbuf = pixbuf.scale_simple(200, 200, GdkPixbuf.InterpType.BILINEAR)
                visual_elements.append(Gtk.Image.new_from_pixbuf(pixbuf))
        except Exception as e:
            logging.error(f"Failed to load image/QR: {e}")

        label = Gtk.Label(label=self.text.strip(), wrap=True)
        label.set_name("prompt-text")
        label.set_line_wrap(True)
        label.set_line_wrap_mode(Gtk.WrapMode.WORD)
        label.set_margin_top(10)
        label.set_margin_bottom(10)
        label.set_margin_start(10)
        label.set_margin_end(10)

        if visual_elements:
            visuals_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
            visuals_box.set_valign(Gtk.Align.CENTER)
            visuals_box.set_halign(Gtk.Align.END)
            visuals_box.set_margin_end(15)
            
            for element in visual_elements:
                frame = Gtk.Frame()
                frame.get_style_context().add_class("visual-frame")
                align = Gtk.Alignment.new(0.5, 0.5, 1, 1)
                align.set_padding(10, 10, 10, 10)
                align.add(element)
                frame.add(align)
                visuals_box.pack_start(frame, False, False, 0)

            content_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=20)
            content_box.set_valign(Gtk.Align.CENTER)
            content_box.get_style_context().add_class("content-box")
            
            text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            text_box.pack_start(label, True, True, 0)
            content_box.pack_start(text_box, True, True, 0)
            
            content_box.pack_end(visuals_box, False, False, 0)
        else:
            content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            label.set_halign(Gtk.Align.CENTER)
            label.set_valign(Gtk.Align.CENTER)
            content_box.set_valign(Gtk.Align.CENTER)
            content_box.set_hexpand(True)
            content_box.set_vexpand(True)
            content_box.pack_start(label, True, True, 20)

        align = Gtk.Alignment.new(0.5, 0.5, 1, 1)
        align.add(content_box)

        self.scroll_box.pack_start(align, True, True, 0)

        scroll = self.gtk.ScrolledWindow(steppers=False)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.add(self.scroll_box)

        content = Gtk.Grid()
        if not self.screen.windowed:
            content.attach(title, 0, 0, 1, 1)
            content.attach(close, 1, 0, 1, 1)
        content.attach(scroll, 0, 1, 2, 1)

        self.prompt = self.gtk.Dialog(
            self.window_title,
            self.buttons,
            content,
            self.response,
        )
        self.prompt.connect("key-press-event", self._key_press_event)
        self.prompt.connect("delete-event", self.close)
        self.screen.screensaver.close()

    def response(self, dialog, response_id):
        for button in self.buttons:
            if button['response'] == response_id:
                self.screen._send_action(None, "printer.gcode.script", {'script': button['gcode']})

    def close(self, *args):
        script = {'script': 'RESPOND type="command" msg="action:prompt_end"'}
        self.screen._send_action(None, "printer.gcode.script", script)

    def end(self):
        if self.prompt is not None:
            self.gtk.remove_dialog(self.prompt)
        self.prompt = None
        self.screen.prompt = None
        self.image_path = None
        self.qrcode_url = None