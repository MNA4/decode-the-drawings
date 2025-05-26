import numpy as np
import pygame as pg
from dataclasses import dataclass

pg.init()
pg.font.init()

@dataclass
class Root:
    screen: pg.Surface
    padding: int = 10

    children = []
    child_bbox = []
    
    def update_layout(self):
        sw, sh = self.screen.get_size()
        max_w = max(self.children, key=lambda x:x.req_width).req_width
        pos = [sw - max_w - self.padding, self.padding]

        self.child_bbox = []
        for i,c in enumerate(self.children[:-1]):
            
            self.child_bbox.append(pg.Rect(pos, (c.req_width, c.req_height)))
            
            pos[1] += c.req_height + self.padding
            if pos[1] + self.children[i+1].req_height + self.padding > sh:
                pos[1] = self.padding
                pos[0] -= max_w - self.padding
            
        self.child_bbox.append(pg.Rect(pos, (self.children[-1].req_width,
                                             self.children[-1].req_height)))

        for i,c in enumerate(self.children):
            c.bbox = self.child_bbox[i]
    
    def process_event(self, event):
        for i in self.children:
            i.process_event(event)
            
        if event.type == pg.VIDEORESIZE and self.children:
            self.update_layout()
            
    def render(self):
        for c in self.children:
            c.render(self.screen)

    def add(self, children):
        self.children.append(children)
        self.update_layout()
        
class BaseWidget:
    def __repr__(self):
        string_repr = self.__class__.__name__
        for attr in self.__dict__:
            if attr in ['in_bbox', 'bbox']:
                continue
            string_repr += f" {attr}={getattr(self, attr)}"
        return string_repr
    
    def __init__(self, parent, *,
                 background=(255, 255, 255),
                 req_width=200,
                 req_height=200):
        """
        :param parent: the container (e.g. Root) that will manage this widget
        :param background: RGB tuple for the widget background (or None for transparent)
        :param req_width: the desired width of this widget
        :param req_height: the desired height of this widget
        """
        self.parent = parent
        self.background = background
        self.req_width = req_width
        self.req_height = req_height
        self.bbox = None  # Will be set by the parent container

        self.parent.add(self)

    def render(self, screen):
        """
        Draws the widget background onto 'screen' if background is set.
        """
        if self.background:
            pg.draw.rect(screen, self.background, self.bbox)

class TitledWidget(BaseWidget):

    font = pg.font.SysFont('consolas', 15)

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

        if padding is None:
            self.padding = self.parent.padding
            
    def render(self, screen):
        super().render(screen)
        if self.title:
            h = self.font.get_height()
            screen.blit(self.font.render(self.title, True, self.foreground),
                            (self.bbox.left + self.padding,
                             self.bbox.top + self.padding)
                        )
                        
            self.in_bbox = pg.Rect(self.bbox.left + self.padding,
                                   self.bbox.top + self.padding * 2 + h,
                                   self.bbox.width - 2 * self.padding,
                                   self.bbox.height - 3 * self.padding - h)
        else:
            self.in_bbox = pg.Rect(self.bbox.left + self.padding,
                                   self.bbox.top + self.padding,
                                   self.bbox.width - 2 * self.padding,
                                   self.bbox.height - 2 * self.padding)
        
if __name__ == "__main__":
    screen = pg.display.set_mode((640, 480))
    clock = pg.time.Clock()
    root = Root(screen)
    widget = TitledWidget(root)
    running = True
    while running:
        for event in pg.event.get():
            if event.type == pg.QUIT:
                running = False
        root.render()
        pg.display.flip()
        clock.tick(30)
        
    pg.quit()
