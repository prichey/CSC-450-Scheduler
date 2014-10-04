from Tkinter import *

font_style = "Helvetica"
size_h1 = 20
size_h2 = 18
size_p = 14

class Page(Frame):
    def __init__(self, root):
        Frame.__init__(self, root)

    def show(self):
        self.lift()

class HomePage(Page):

    def __init__(self, root):
        Frame.__init__(self, root)
        self.head_label = Label(self, text="Welcome", font=(font_style, size_h1))
        self.head_label.pack(pady=10)

        paragraph_text = "To use this scheduler:\n" +\
                         "\t\t - Do this thing if you want this to happen.\n" +\
                         "\t\t - Do that thing if you want that to happen.\n"
        self.description_label = Label(self, text=paragraph_text, font=(font_style, size_p))
        self.description_label.pack()

        self.version_label = Label(self, text="<version info?>")
        self.version_label.pack(side=BOTTOM, pady=5)


class ConstraintPage(Page):

    def __init__(self, root):
        Frame.__init__(self, root)
        self.head_label = Label(self, text="Constraint Page")
        self.head_label.pack()

class ViewPage(Page):

    def __init__(self, root):
        Frame.__init__(self, root)
        self.head_label = Label(self, text="View Page")
        self.head_label.pack()

class MiscPage(Page):

    def __init__(self, root):
        Frame.__init__(self, root)
        self.head_label = Label(self, text="Misc Page")
        self.head_label.pack()

class MainWindow(Frame):

    def __init__(self, root):
        Frame.__init__(self, root)
        self.pack(side = TOP, fill = "both")
        
        # MENU AND CONTENT SECTIONS
        self.menu = Frame(self, width="500", height="600")
        self.menu.pack(side=LEFT, fill="both")

        self.content_container = Frame(self, width="800", height="600")
        self.content_container.pack(side=LEFT, fill="both")

        # MENU BUTTONS
        self.home_btn = Button(self.menu, text='Home', command=self.show_home, \
                               width="10", height="3", font=(font_style, size_h2), cursor = 'hand2') # specified in characters?
        self.home_btn.pack(fill=X, side="top", pady=2)
        
        self.constraint_btn = Button(self.menu, text='Constraint', command=self.show_constraint, \
                               width="10", height="3", font=(font_style, size_h2), cursor = 'hand2')
        self.constraint_btn.pack(fill=X, side="top", pady=2)
        
        self.view_btn = Button(self.menu, text='View', command=self.show_view, \
                               width="10", height="3", font=(font_style, size_h2), cursor = 'hand2')
        self.view_btn.pack(fill=X, side="top", pady=2)
        
        self.misc_btn = Button(self.menu, text='Misc', command=self.show_misc, \
                               width="10", height="3", font=(font_style, size_h2), cursor = 'hand2')
        self.misc_btn.pack(fill=X, side="top", pady=2)
        
        self.run_btn = Button(self.menu, text='RUN', bg='green', command=self.run_scheduler, \
                               width="10", height="3", font=(font_style, size_h2), cursor = 'hand2')
        self.run_btn.pack(fill = X, side = "top", pady=2)

        # PAGES
        self.home_page = HomePage(self.content_container)
        self.home_page.place(in_=self.content_container, x=0, y=0, relwidth=1, relheight=1)
        
        self.constraint_page = ConstraintPage(self.content_container)
        self.constraint_page.place(in_=self.content_container, x=0, y=0, relwidth=1, relheight=1)
        
        self.view_page = ViewPage(self.content_container)
        self.view_page.place(in_=self.content_container, x=0, y=0, relwidth=1, relheight=1)
        
        self.misc_page = MiscPage(self.content_container)
        self.misc_page.place(in_=self.content_container, x=0, y=0, relwidth=1, relheight=1)

        # INITIALIZE WITH HOME PAGE
        self.home_page.lift()
        
    def show_home(self):
        self.home_page.lift()

    def show_constraint(self):
        self.constraint_page.lift()

    def show_view(self):
        self.view_page.lift()

    def show_misc(self):
        self.misc_page.lift()

    def run_scheduler(self):
        return
