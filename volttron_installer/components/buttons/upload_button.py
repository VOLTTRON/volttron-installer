import reflex as rx

def upload_button( **props ) -> rx.Component:
    return rx.el.div(
        rx.hstack(
            rx.el.div(
                rx.html(
                '''
                    <svg class-name="upload_svg" width="2rem" height="2rem" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path opacity="0.5" d="M3 15C3 17.8284 3 19.2426 3.87868 20.1213C4.75736 21 6.17157 21 9 21H15C17.8284 21 19.2426 21 20.1213 20.1213C21 19.2426 21 17.8284 21 15" 
                        stroke="#ffffff" 
                        stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"
                        />
                    <path d="M12 16V3M12 3L16 7.375M12 3L8 7.375" 
                        stroke="#ffffff" 
                        stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
                    </svg>
                '''
                ),
                class_name="upload_svg_container"
            ),
            rx.el.div(
                "Upload File",
                class_name="upload-button-text-container"
            ),
            align="center",
            justify="center",
            spacing="2"
        ),
        style={
            "_hover" : {
                "background-color" : "#2A2A2C"
            }
        },
        class_name="upload_button",
        **props
    )