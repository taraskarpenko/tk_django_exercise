def preprocessing_filter_spec(endpoints):
    """remove api/schema/ endpoints from OpenAPI documentation"""
    return filter(
        lambda endpoint: "api/schema/" not in endpoint[0],
        endpoints
    )
