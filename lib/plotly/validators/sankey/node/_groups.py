import _plotly_utils.basevalidators


class GroupsValidator(_plotly_utils.basevalidators.InfoArrayValidator):

    def __init__(
        self, plotly_name='groups', parent_name='sankey.node', **kwargs
    ):
        super(GroupsValidator, self).__init__(
            plotly_name=plotly_name,
            parent_name=parent_name,
            dimensions=kwargs.pop('dimensions', 2),
            edit_type=kwargs.pop('edit_type', 'calc'),
            free_length=kwargs.pop('free_length', True),
            items=kwargs.pop(
                'items', {
                    'valType': 'number',
                    'editType': 'calc'
                }
            ),
            role=kwargs.pop('role', 'info'),
            **kwargs
        )
