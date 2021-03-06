import argparse

def _parse_number(x):
    try:
        return int(x)
    except ValueError:
        return float(x)


def vue_dtype(field):
    t_ = field["type"]
    if t_ == "input":
        it_ = field["inputType"]
        if it_ == "number":
            return _parse_number
        else:
            return str
    elif t_ == "checkbox":
        return bool
    else:
        return str


def parse_settings_args(schema):
    parser = argparse.ArgumentParser()
    for f in schema["fields"]:
        if "model" in f:
            parser.add_argument("--{model}".format(**f), help=f.get("label", ""), type=vue_dtype(f))

    settings = {}
    for k, v in vars(parser.parse_known_args()[0]).items():
        if v is not None:
            path = k.split(".")
            x = settings
            for n in path[:-1]:
                x = x.setdefault(n, {})
            else:
                x[path[-1]] = v

    return settings


def label(label):
    return dict(
        type="label",
        label=label
    )


def input_field(label, model, default, required):
    return dict(
        label=label,
        model=model,
        default=default,
        required=required,
    )


def number_input(label, model, default, required, min=0, max=100, step=1):
    return dict(
        type="input",
        inputType="number",
        min=min,
        max=max,
        **input_field(label, model, default, required)
    )


def text_input(label, model, default="", required=True):
    return dict(
        type="input",
        inputType="text",
        **input_field(label, model, default, required)
    )


def text_area(label, model, default, required, hint, max, placeholder, rows):
    return dict(
        type="textArea",
        hint=hint,
        placeholder=placeholder,
        rows=rows,
        max=max,
        **input_field(label, model, default, required)
    )


def checkbox(label, model, default, required):
    return dict(
        type="checkbox",
        **input_field(label, model, default, required)
    )


def select(label, model, default, required, values):
    return dict(
        type="select",
        values=values,
        **input_field(label, model, default, required)
    )
