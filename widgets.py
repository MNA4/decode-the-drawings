import pygame as pg

pg.init()
pg.font.init()

class Root:
    """
    Root container for all widgets.
    """
    def __repr__(self):
        string_repr = self.__class__.__name__
        for attr in self.__dict__:
            string_repr += f" {attr}={getattr(self, attr)}"
        return '<'+string_repr+'>'
    def __init__(self, screen: pg.Surface, *, padding: int = 10):
        """
        :param screen: the main pygame Surface to draw onto
        :param padding: spacing to apply around child widgets
        """
        self.screen = screen
        self.padding = padding

        self.children = []
        self.child_bbox = []

    def update_layout(self):
        """
        Updates the layout of child widgets based on their required sizes.
        """
        sw, sh = self.screen.get_size()
        max_w = max(self.children, key=lambda x:x.req_width).req_width
        pos = [sw - max_w - self.padding, self.padding]

        self.child_bbox = []
        for i,c in enumerate(self.children[:-1]):

            self.child_bbox.append(pg.Rect(pos, (c.req_width, c.req_height)))

            pos[1] += c.req_height + self.padding
            if pos[1] + self.children[i+1].req_height + self.padding > sh:
                pos[1] = self.padding
                pos[0] -= max_w + self.padding

        self.child_bbox.append(pg.Rect(pos, (self.children[-1].req_width,
                                             self.children[-1].req_height)))

        for i,c in enumerate(self.children):
            c.bbox = self.child_bbox[i]
            c.update_layout()

    def process_event(self, event):
        """
        Processes events for all widgets.
        :param event: pygame event to process
        """
        for i in self.children:
            i.process_event(event)

        if event.type == pg.VIDEORESIZE and self.children:
            self.update_layout()

    def render(self):
        """
        Renders all child widgets onto the screen.
        """
        for c in self.children:
            c.render(self.screen)

    def add(self, children):
        """
        Adds a widget or list of widgets to the root container.
        Don't use this method directly; use the widget constructors instead.
        :param children: a single widget or a list of widgets to add
        """
        if isinstance(children, list):
            self.children.extend(children)
        else:
            self.children.append(children)

class BaseWidget:
    """
    Base class for all widgets.
    """
    def __repr__(self):
        string_repr = self.__class__.__name__
        for attr in self.__dict__:
            if attr in ['in_bbox', 'bbox']:
                continue
            string_repr += f" {attr}={getattr(self, attr)}"
        return '<'+string_repr+'>'

    def __init__(self, parent, *,
                 background=None,
                 req_width=200,
                 req_height=200,
                 padding=None):
        """
        :param parent: the container (e.g. Root) that will manage this widget
        :param background: RGB tuple for the widget background (or None for transparent)
        :param req_width: the desired width of this widget
        :param req_height: the desired height of this widget
        :param padding: spacing to apply around child widgets (optional)
        """
        self.parent = parent
        self.background = background
        self.req_width = req_width
        self.req_height = req_height
        self.bbox = None  # Will be set by the parent container
        self.children = []
        self.child_bbox = []
        if padding is not None:
            self.padding = padding
        else:
            self.padding = self.parent.padding

        self.parent.add(self)

    def update_layout(self):
        """
        Updates the layout of this widget.
        """
        if self.children:
            # Simple vertical layout: stack children top-to-bottom inside self.bbox with padding
            x = self.bbox.left + self.padding
            y = self.bbox.top + self.padding
            width = self.bbox.width - 2 * self.padding
            self.child_bbox = []
            for c in self.children:
                c.bbox = pg.Rect(x, y, min(c.req_width, width), c.req_height)
                self.child_bbox.append(c.bbox)
                y += c.req_height + self.padding
 
        for i, c in enumerate(self.children):
            c.bbox = self.child_bbox[i]
            c.update_layout()

    def render(self, screen):
        """
        Draws the widget background onto 'screen' if background is set.
        :param screen: the pygame Surface to draw onto
        """
        if self.background:
            pg.draw.rect(screen, self.background, self.bbox)

        for c in self.children:
            c.render(screen)

    def process_event(self, event):
        """
        Processes events for this widget.
        """
        for c in self.children:
            c.process_event(event)

        # Default implementation does nothing, override in subclasses if needed

    def add(self, children):
        """
        Adds a widget or list of widgets to this widget.
        Don't use this method directly; use the widget constructors instead.
        By default, widgets doesn't do anything with children.
        :param children: a single widget or a list of widgets to add
        """
        if isinstance(children, list):
            self.children.extend(children)
        else:
            self.children.append(children)


class Label(BaseWidget):
    """
    A simple text label widget.
    """
    def __init__(self, parent, font, *,
                 text="Sample Label",
                 background=None,
                 foreground=(0, 0, 0),
                 align="left"):
        """
        :param parent: the container (e.g. Root) that will manage this widget
        :param font: pygame Font object to use for rendering text
        :param text: the text to display in the label
        :param background: RGB tuple for the widget background (or None for transparent)
        :param foreground: RGB tuple for the text color
        :param align: text alignment: 'left', 'center', or 'right'
        """
        super().__init__(
            parent,
            background=background,
            req_width=None,  # Width will be determined by text
            req_height=None,  # Height will be determined by text
        )
        self.font = font
        self.text = text
        self.foreground = foreground
        self.align = align
        self.req_width, self.req_height = self.font.size(self.text)

    def update_layout(self):
        super().update_layout()
        self.req_width, self.req_height = self.font.size(self.text)

    def render(self, screen):
        """
        Renders the label text onto the screen.
        :param screen: the pygame Surface to draw onto
        """
        super().render(screen)
        if self.text:
            text_surface = self.font.render(self.text, True, self.foreground)
            text_rect = text_surface.get_rect()
            # Align text within self.bbox
            if self.align == "center":
                text_rect.center = self.bbox.center
            elif self.align == "right":
                text_rect.midright = self.bbox.midright
            else:  # "left" or fallback
                text_rect.midleft = self.bbox.midleft
            screen.blit(text_surface, text_rect)

class Slider(BaseWidget):
    """
    A simple horizontal slider widget.
    """
    def __init__(self, parent, *,
                 min_val=0.0,
                 max_val=1.0,
                 value=0.5,
                 track_height=10,
                 background=None,
                 thumb_color=(50, 50, 50),
                 track_color=(100, 100, 100),
                 req_width=200,
                 req_height=20):
        """
        :param min_val: minimum slider value
        :param max_val: maximum slider value
        :param value: initial value (clamped between min_val and max_val)
        :param track_height: thickness of the track
        """
        super().__init__(
            parent,
            background=background,
            req_width=req_width,
            req_height=req_height,
        )
        self.min = min_val
        self.max = max_val
        self.value = max(min_val, min(max_val, value))
        self.track_h = track_height
        self.track_color = track_color
        self.thumb_color = thumb_color
        self.thumb_width = req_height # Thumb is square, so width == height
        self.thumb_height = req_height

        self.dragging = False  

    def _value_to_pos(self) -> int:
        """Convert current value to an x-coordinate for the thumb center.
        :return: x-coordinate for the thumb center"""
        left = self.bbox.left + self.thumb_width // 2
        right = self.bbox.right - self.thumb_width // 2
        frac = (self.value - self.min) / (self.max - self.min)
        return int(left + frac * (right - left))

    def _pos_to_value(self, x: int) -> float:
        """Convert an x-coordinate to a value in [min, max].
        :param x: x-coordinate to convert
        :return: value in the range [min, max]
        """
        left = self.bbox.left + self.thumb_width // 2
        right = self.bbox.right - self.thumb_width // 2
        frac = (x - left) / (right - left)
        return max(self.min, min(self.max, self.min + frac * (self.max - self.min)))

    def process_event(self, event: pg.event.Event) -> bool:
        """
        Processes events.
        :param event: pygame event to process
        :return: True if the value changed, False otherwise
        """
        changed = False
        if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            # If click anywhere inside the slider bbox, jump thumb and start dragging
            if self.bbox.collidepoint(event.pos):
                mx, _ = event.pos
                self.value = self._pos_to_value(mx)
                self.dragging = True
                changed = True

        elif event.type == pg.MOUSEBUTTONUP and event.button == 1:
            self.dragging = False

        elif event.type == pg.MOUSEMOTION and self.dragging:
            mx, _ = event.pos
            new_val = self._pos_to_value(mx)
            if new_val != self.value:
                self.value = new_val
                changed = True
        return changed

    def render(self, screen):
        """
        Renders the widget.
        :param screen: the pygame Surface to draw onto
        """
        # Draw background
        super().render(screen)

        # Track
        track_rect = pg.Rect(
            self.bbox.left,
            self.bbox.centery - self.track_h // 2,
            self.bbox.width,
            self.track_h
        )
        pg.draw.rect(screen, self.track_color, track_rect)

        # Thumb
        thumb_x = self._value_to_pos()
        thumb_y = self.bbox.centery
        pg.draw.rect(
            screen,
            self.thumb_color,
            (
            thumb_x - self.thumb_width // 2,
            thumb_y - self.thumb_height // 2,
            self.thumb_width,
            self.thumb_height
            )
        )

class RadioButtons(BaseWidget):
    """
    A simple vertical list of radio buttons using Label widgets.
    """
    def __init__(self, parent, *,
                 options,
                 selected=0,
                 font=None,
                 background=None,
                 foreground=(0, 0, 0),
                 req_width=200,
                 req_height=None,
                 padding=None,
                 spacing=5):
        """
        :param parent: the container (e.g. Root) that will manage this widget
        :param options: list of string options
        :param selected: index of initially selected option
        :param font: pygame Font object
        :param background: RGB tuple for the widget background (or None for transparent)
        :param foreground: RGB tuple for the text color
        :param req_width: the desired width of this widget
        :param req_height: the desired height of this widget (auto if None)
        :param padding: spacing to apply around child widgets (optional)
        :param spacing: vertical space between radio buttons
        """
        super().__init__(
            parent,
            background=background,
            req_width=req_width,
            req_height=req_height,
            padding=padding
        )
        self.options = options
        self.selected = selected
        self.font = font
        self.foreground = foreground
        self.spacing = spacing
        self.circle_radius = self.font.get_height() // 2
        self.labels = [
            Label(self,
                  font=self.font,
                  text=option,
                  background=None, 
                  foreground=self.foreground,
                  align="left")
            for option in options
        ]
        # Calculate required height
        total_height = len(options) * (self.font.get_height() + self.spacing) - \
                       self.spacing + 2 * self.padding
        self.req_height = total_height

    def update_layout(self):
        # Position each label and store its bbox for hit testing
        y = self.bbox.top + self.padding
        for label in self.labels:
            label.bbox = pg.Rect(
                self.bbox.left + self.padding + 2 * self.circle_radius + self.spacing,
                y,
                self.bbox.width - 2 * self.padding - 2 * self.circle_radius - self.spacing,
                self.font.get_height()
            )
            y += self.font.get_height() + self.spacing

    def process_event(self, event):
        if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            y = self.bbox.top + self.padding
            for i in range(len(self.labels)):
                # The clickable area includes the circle and the label
                rect = pg.Rect(
                    self.bbox.left + self.padding,
                    y,
                    self.bbox.width - 2 * self.padding,
                    self.font.get_height()
                )
                if rect.collidepoint(mx, my):
                    self.selected = i
                    break
                y += self.font.get_height() + self.spacing

    def render(self, screen):
        super().render(screen)

        circle_x = self.bbox.left + self.padding + self.circle_radius
        circle_y = self.bbox.top + self.padding + self.circle_radius
        for i in range(len(self.labels)):
            # Draw radio circle
            pg.draw.circle(screen, self.foreground, (circle_x, circle_y), self.circle_radius, 2)
            if i == self.selected:
                pg.draw.circle(screen,
                               self.foreground,
                               (circle_x, circle_y),
                               self.circle_radius - 4)
            circle_y += self.font.get_height() + self.spacing


class TitledWidget(BaseWidget):
    """
    A base widget with a title at the top.
    """

    title_font = pg.font.SysFont('consolas', 15, bold=True)

    def __init__(self, parent,
                 *,
                 padding=None,
                 background=(255, 255, 255),
                 foreground=(0, 0, 0),
                 req_width=200,
                 req_height=200,
                 title="Sample Widget"):
        """
        :param parent: the container (e.g. Root) that will manage this widget
        :param padding: padding around the content inside the widget
        :param background: RGB tuple for the widget background (or None for transparent)
        :param foreground: RGB tuple for the text color
        :param req_width: the desired width of this widget
        :param req_height: the desired height of this widget
        :param title: the title text to display at the top of the widget
        """

        super().__init__(
            parent,
            background=background,
            req_width=req_width,
            req_height=req_height,
        )

        self.foreground = foreground
        self.in_bbox = None
        self.title = title

        self.title_label = Label(
            self,
            font=self.title_font,
            text=self.title,
            background=None,
            foreground=self.foreground
        )
            
    def update_layout(self):
        """ Updates the layout of this widget based on its title and padding.
        This sets the in_bbox to the area where content should be drawn.
        """
        self.title_label.text = self.title
        if self.title:
            h = self.title_font.get_height()
            self.in_bbox = pg.Rect(self.bbox.left + self.padding,
                                   self.bbox.top + self.padding * 2 + h,
                                   self.bbox.width - 2 * self.padding,
                                   self.bbox.height - 3 * self.padding - h)
        else:
            self.in_bbox = pg.Rect(self.bbox.left + self.padding,
                                   self.bbox.top + self.padding,
                                   self.bbox.width - 2 * self.padding,
                                   self.bbox.height - 2 * self.padding)
            
        super().update_layout()
            

class SettingsWidget(TitledWidget):
    """
    A widget for displaying and adjusting settings.
    """
    settings_font = pg.font.SysFont('consolas', 12, bold=True)
    settings_label_font = pg.font.SysFont('consolas', 12, bold=False)
    def __init__(self, parent, *,
                 padding=None,
                 background=(255, 255, 255),
                 foreground=(0, 0, 0),
                 req_width=200,
                 attributes=(
                     {"type": "slider", 
                      "min": 0.0, 
                      "max": 100.0, 
                      "value": 50.0, 
                      "name": "Sample Slider"},
                      ),
                 title="Settings"):
        """
        :param parent: the container (e.g. Root) that will manage this widget
        :param padding: padding around the content inside the widget
        :param background: RGB tuple for the widget background (or None for transparent)
        :param foreground: RGB tuple for the text color
        :param req_width: the desired width of this widget
        :param req_height: the desired height of this widget
        :param title: the title text to display at the top of the widget
        """
        super().__init__(
            parent,
            padding=padding,
            background=background,
            foreground=foreground,
            req_width=req_width,
            req_height=None,  # Height will be determined by content
            title=title
        )
        self.settings_widgets = []
        self.req_height = self.title_font.get_height() - self.padding
        self.attributes = attributes
        for attr in self.attributes:
            if attr["type"] == "slider":
                label = Label(
                    self,
                    font=self.settings_font,
                    text=attr.get("name", "Unnamed Slider"),
                    background=None,
                    foreground=self.foreground
                )
                min_label = Label(
                    self,
                    font=self.settings_label_font,
                    text=str(attr["min"]),
                    background=None,
                    foreground=self.foreground,
                    align="left"
                )
                value_label = Label(
                    self,
                    font=self.settings_label_font,
                    text=str(attr["value"]),
                    background=None,
                    foreground=self.foreground,
                    align="center"
                )
                max_label = Label(
                    self,
                    font=self.settings_label_font,
                    text=str(attr["max"]),
                    background=None,
                    foreground=self.foreground,
                    align="right"
                )
                slider = Slider(self,
                            min_val=attr["min"],
                            max_val=attr["max"],
                            value=attr["value"])
                self.req_height += (slider.req_height + self.padding) * 3  # Slider + label
                self.settings_widgets.append({
                    "type": "slider",
                    "label": label,
                    "slider": slider,
                    "min_label": min_label,
                    "value_label": value_label,
                    "max_label": max_label
                })

    def update_layout(self):
        """ Updates the layout of this widget based on its title and padding.
        This sets the in_bbox to the area where content should be drawn.
        """
        super().update_layout()

        y = self.in_bbox.top
        for s in self.settings_widgets:
            if s["type"] == "slider":
                for c in s["label"], s["value_label"], s["slider"]:
                    bbox = pg.Rect(
                            self.in_bbox.left,
                            y,
                            self.in_bbox.width,
                            c.req_height
                        )
                    if c == s["value_label"]:
                        s["value_label"].bbox = \
                        s["min_label"].bbox = \
                        s["max_label"].bbox = bbox
                    else:
                        c.bbox = bbox
                    y += c.req_height + self.padding

    def process_event(self, event) -> bool:
        """
        Processes events for all sliders in this widget.
        :param event: pygame event to process
        """
        for i, s in enumerate(self.settings_widgets):
            if s["type"] != "slider":
                continue
            slider = s["slider"]
            changed = slider.process_event(event)
            if changed:
                self.attributes[i]["value"] = slider.value
                s["value_label"].text = f"{slider.value:.2f}"

if __name__ == "__main__":
    screen = pg.display.set_mode((640, 480), pg.RESIZABLE)
    pg.display.set_caption("Widget Example")

    clock = pg.time.Clock()
    root = Root(screen)
    widget = TitledWidget(root)
    settings = SettingsWidget(root,
                              attributes=[
                                  {
                                      "type": "slider", 
                                      "min": 0, 
                                      "max": 100, 
                                      "value": 50, 
                                      "name": "Volume"
                                      },
                                  {
                                      "type": "slider", 
                                      "min": 0, 
                                      "max": 1, 
                                      "value": 0.5, 
                                      "name": "Brightness"
                                      }
                              ],
                              title="Settings")
    radio = RadioButtons(
        root,
        options=["Option 1", "Option 2", "Option 3"],
        selected=1,
        font=pg.font.SysFont('consolas', 12),
        background=(255, 255, 255),
        foreground=(0, 0, 0),
        req_width=200,
        padding=10
    )
    root.update_layout() # Don't forget to call this after adding widgets
    running = True
    while running:
        for event in pg.event.get():
            if event.type == pg.QUIT:
                running = False
            root.process_event(event)

        screen.fill((0, 0, 0))
        root.render()
        pg.display.flip()
        clock.tick(30)

    pg.quit()
