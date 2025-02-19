"""
Wasted too much time on this but it could work once we actually get to the point of working on it
"""

from flet import *

from volttron_installer.modules.styles import modal_styles, progress_styles

class ProgressBar:
    def __init__(self, page: Page, step: str):
        self.page = page
        self.styles = progress_styles()
        self.step = step
        
        self.separating_line: Container = Container(
             width=4,
             height=40,
             bgcolor=self.styles['default_color'],
             margin=margin.only(left=15.3),
             animate=None
            )
        self.breathing_circle = Container(
             #starting width and height because we need to start breathing 
             width=17,
             height=17,
             border_radius=200,
             bgcolor=colors.with_opacity(0.55, self.styles['default_color']),
             animate=None
        )
        self.completed_step_circle=Container(
             content=Icon(name=icons.CHECK, color=self.styles['check_color'])
        )
        
        # set breathing in, out, size
        self.fully_exhauled_size = 17
        self.fully_inhaled_size = 32

        self.out_most_ring_with_current_step = Row(
            controls=[
                Container(
                    width=35,
                    height=35,
                    border_radius=50,
                    border=border.all(2.5, self.styles['default_color']),
                    content=Stack(
                        alignment=alignment.center,
                        controls=[]
                    )
                ),
                Text(value=self.step, color="black")
            ]
        )
        
    def animate_breathing_dot(self)-> None:
        import time

        self.out_most_ring_with_current_step.content.controls.append(self.breathing_circle)
        self.out_most_ring_with_current_step.update()

        # ++ 1 every loop and puts this into a function, this variable will be an arg of a func and 
        # when test_iterations == 5, we will end the animation
        test_iterations = 0

        # We are waiting for the step to complete, we are breathing
        completed = False
        holding_in_breath = False
        while completed:
                # width == 17, this means that we need to take in a breathe because our lungs or depressed
                if self.breathing_circle.width == 17:

                    #set BREATHE IN animation
                    self.breathing_circle.animate = animation.Animation(4000, AnimationCurve.EASE_IN_OUT)
                    
                    #set new width, bgcolor, and height
                    self.breathing_circle.width = self.fully_inhaled_size
                    self.breathing_circle.height = self.fully_inhaled_size
                    self.breathing_circle.bgcolor = self.styles['completed']
                    
                    # allow time for the animation to finish before going through the loop body again
                    time.sleep(4.4)

                    #because we just took in a deep breathe, we are now holding it in
                    holding_in_breath = True
                
                #if width wasnt 17, we are actually holding in our breath and need to exhale
                else:
                    
                    #Set BREATHE OUT animation
                    self.breathing_circle.animate = animation.Animation(8000, AnimationCurve.EASE_IN)
                    
                    self.breathing_circle.width = self.fully_exhauled_size
                    self.breathing_circle.height = self.fully_exhauled_size
                    self.breathing_circle.bgcolor = colors.with_opacity(0.55, self.styles['default_color']),

                    time.sleep(8.4)
                    
                if holding_in_breath:
                     # I just took in a deep breathe, need to hold it in
                     time.sleep(3)
                     holding_in_breath = False
                else:
                     # I dont have a breathe in my lungs, im going to wait to take another one in
                    time.sleep(2)
                
                #update the control
                self.breathing_circle.update()
                
                #testing block
                test_iterations =+ 1

                if self.check_if_completed(test_iterations):
                    completed = True

        self.animate_completed_step()

    def animate_completed_step(self) -> None:
         
         #code block updating the line connecting to the circle,
         self.separating_line.animate = animation.Animation(2000, AnimationCurve.EASE_IN_OUT_QUART)
         self.separating_line.bgcolor = self.styles['completed']
         self.separating_line.update()
         pass

    #this function will eventually be awesome and be able to communicate with the backend to see if it is actually completed
    def check_if_completed(self, arg) -> bool:
        if arg == 5:
             # print(f"We are on the {arg} iteration, we will stop now.")
             return True
        # print(f"We are on the {arg} iteration, we will keep going.")
        return False

    def build_structure(self):
        return Container(
             content=Column(
                  self.out_most_ring_with_current_step
             )
        )
    

class DeployToPlatformModal:
    """"
    Container for the progress bar. The modal will be built here
and exported into a different file where the build will take place
and display itself.
"""
    def __init__(self):
            self.modal_content=Column(
                 horizontal_alignment=CrossAxisAlignment.CENTER,
                 controls=[]
            )
            self.modal_structure = AlertDialog(
                modal=True,
                bgcolor="#00000000",
                content=Container(
                    **modal_styles(),
                    width=600,
                    height=800,
                    content=self.modal_content
                ),
            )

    def return_modal(self)-> Container:
         return self.modal_structure