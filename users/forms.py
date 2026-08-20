from django import forms

from .permissions import assignable_agents


class AgentReassignmentForm(forms.Form):
    agent = forms.ModelChoiceField(
        label="Nuevo agente responsable",
        queryset=assignable_agents(),
        empty_label=None,
        widget=forms.Select(
            attrs={
                "class": (
                    "w-full rounded-xl border border-gray-300 bg-white px-4 "
                    "py-3 text-gray-900 shadow-sm focus:border-blue-500 "
                    "focus:outline-none focus:ring-2 focus:ring-blue-200"
                )
            }
        ),
    )

    def __init__(self, *args, current_agent=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["agent"].queryset = assignable_agents(current_agent)
        if current_agent is not None:
            self.fields["agent"].initial = current_agent
