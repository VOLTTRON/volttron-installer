"""
On initialization with PlatformTile, they append themselves to dynamic routes like this:

``python
dynamic_routes[self.platform.generated_url] = view
``

dynamic_routes will now look something like this:

``python
dynamic_routes = {"/abcdef" : View}
``

"""
dynamic_routes = {}