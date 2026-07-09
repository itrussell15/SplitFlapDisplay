from fastapi import Request

def get_display(request: Request):
    return request.app.state.display

def get_rate_limiter(request: Request):
    return request.app.state.rate_limiter