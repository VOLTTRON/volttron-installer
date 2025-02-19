from pydantic import BaseModel
from functools import partial

from .home import home_view
from .config_manager import config_manager_view
from .platform_manager import platform_manager_view
from .deploy_platform import deploy_platform_view

class _InstallerView(BaseModel):
    route: str
    instance: object


class _InstallerViews(BaseModel):
    home: _InstallerView = _InstallerView(route="/", instance=partial(home_view))
    config_manager: _InstallerView = _InstallerView(route="/config_manager",
                                                    instance=partial(
                                                        config_manager_view,
                                                        message="Woot this is a message sent"))
    platform_manager: _InstallerView = _InstallerView(route="/platform_manager",
                                                instance=partial(platform_manager_view))
    deploy_platform: _InstallerView = _InstallerView(route="/deploy_platform",
                                                     instance=partial(deploy_platform_view))
    # sender: _InstallerView = _InstallerView(route="/sender",
    #                                 instance=partial(
    #                                     sender_view,
    #                                     get_certificates=get_certificates))
    # subscriber: _InstallerView = _InstallerView(route="/subscriber",
    #                                     instance=partial(
    #                                         subscriber_view,
    #                                         get_certificates=get_certificates))

    def __getitem__(self, item):
        return getattr(self, item)

    def __iter__(self):
        for page in self.__dict__.values():
            yield page


InstallerViews = _InstallerViews()


