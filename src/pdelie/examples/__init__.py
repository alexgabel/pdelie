__all__ = ["run_heat_vertical_slice_example", "run_kdv_vertical_slice_example"]


def run_heat_vertical_slice_example() -> dict[str, object]:
    from pdelie.examples.heat_vertical_slice import run_heat_vertical_slice_example as _impl

    return _impl()


def run_kdv_vertical_slice_example() -> dict[str, object]:
    from pdelie.examples.kdv_vertical_slice import run_kdv_vertical_slice_example as _impl

    return _impl()
