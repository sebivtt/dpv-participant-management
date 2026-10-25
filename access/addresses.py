"""Gerüst der Markierungen für den Rundumtest (#90); die Regeln folgen."""


def checks_rights(*row_ids: str):
    def mark(view):
        return view

    return mark


def without_personal_data(reason: str):
    def mark(view):
        return view

    return mark
