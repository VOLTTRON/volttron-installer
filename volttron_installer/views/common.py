from flet import Dropdown, dropdown, Ref
from uudex_web.data.certificates import Certificate
from uudex_api_client.models import Subject, Subscription
from typing import Callable, Optional


def build_certificates_dropdown(get_certificates: Callable,
                                on_change: Callable,
                                ref: Optional[Ref] = None) -> Dropdown:

    certs: list[Certificate] = get_certificates()
    drp_down = Dropdown(
        label="Select Certificate for API",
        ref=ref,
        options=[
            dropdown.Option(text=cert.name, key=cert.name)
            for cert in sorted(certs, key=lambda cert: cert.name)
        ],
        on_change=on_change,
        width=500)
    return drp_down


def build_subject_dropdown(get_subjects: Callable,
                           on_change: Callable,
                           ref: Optional[Ref] = None) -> Dropdown:

    subjects: list[Subject] = get_subjects()

    options = [
        dropdown.Option(text=subject.subject_name, key=subject.subject_name)
        for subject in sorted(subjects,
                              key=lambda subject: subject.subject_name)
    ]

    if ref is not None and ref.current is not None:
        ref.current.options = options
        drp_down = ref.current
    else:
        drp_down = Dropdown(label="Select Subject for API",
                            ref=ref,
                            options=options,
                            on_change=on_change,
                            width=500)
    return drp_down


def build_subscription_dropdown(get_subscriptions: Callable,
                                on_change: Callable,
                                ref: Optional[Ref] = None) -> Dropdown:

    subscriptions: list[Subscription] = get_subscriptions()

    options = [
        dropdown.Option(text=subscription.subscription_name,
                        key=subscription.subscription_uuid) for subscription in
        sorted(subscriptions,
               key=lambda subscription: subscription.subscription_name)
    ]

    if ref is not None and ref.current is not None:
        ref.current.options = options
        drp_down = ref.current
    else:
        drp_down = Dropdown(label="Select Subscription for API",
                            ref=ref,
                            options=options,
                            on_change=on_change,
                            width=500)
    return drp_down
