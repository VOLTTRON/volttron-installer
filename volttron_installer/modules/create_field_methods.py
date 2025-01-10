from flet import Container, Text, Row, padding, Divider

# create a field pair 
def field_pair(field_title, input) -> Container:
    return Container(
        #height=70,
        padding=padding.only(top=10, bottom=10, left=5, right=5),
        content=Row(
            controls=[
                Container(expand=2, content=Text(f"{field_title}", size=20)),
                Container(expand=3, content=input)
            ],
            spacing=0
        )
    )

# Divide all the fields up between dividers
def divide_fields(field_list) -> list:
    div = Divider(height=9, thickness=3, color="white")
    return [element for pair in zip(field_list, [div] * (len(field_list) - 1)) for element in pair] + [field_list[-1], div]