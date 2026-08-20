from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from goals.models import Goal
from goals.services import calculate_progress
from users.models import User


class Command(BaseCommand):
    help = "Crea objetivos de prueba variados de forma idempotente"

    marker = "[DEMO OBJETIVOS]"

    @transaction.atomic
    def handle(self, *args, **options):
        creator = User.objects.filter(
            is_active=True,
            role__in=["admin", "manager"],
        ).order_by("-is_superuser", "id").first()
        if creator is None:
            creator = User.objects.filter(is_active=True, is_superuser=True).first()
        if creator is None:
            raise CommandError(
                "Se necesita al menos un administrador o manager activo para crear los objetivos."
            )

        agents = list(
            User.objects.filter(is_active=True, role="agent").order_by("id")
        )
        if len(agents) < 2:
            raise CommandError(
                "Se necesitan al menos dos agentes activos. Crea o carga agentes antes de ejecutar este comando."
            )

        by_username = {agent.username: agent for agent in agents}

        def agent(preferred_username, fallback_index=0):
            return by_username.get(
                preferred_username,
                agents[min(fallback_index, len(agents) - 1)],
            )

        carlos = agent("Carlos", 0)
        marta = agent("Marta", 1)
        integral = agent("demo_flujo_integral", 0)
        operaciones = agent("demo_operaciones", 1)
        demo_team = list(dict.fromkeys([marta, integral, operaciones]))
        if len(demo_team) < 2:
            demo_team = agents[: min(3, len(agents))]

        today = timezone.localdate()
        scenarios = [
            {
                "name": "[DEMO] Captación de contactos conseguida",
                "scope": "individual",
                "metric": "contacts",
                "start_date": today - timedelta(days=30),
                "end_date": today + timedelta(days=10),
                "assignees": [carlos],
                "target_mode": "achieved",
                "description": "Objetivo individual activo que permite comprobar el estado conseguido.",
            },
            {
                "name": "[DEMO] Impulso de nuevas noticias",
                "scope": "individual",
                "metric": "news",
                "start_date": today - timedelta(days=60),
                "end_date": today + timedelta(days=20),
                "assignees": [integral],
                "target_mode": "partial",
                "target_gap": 3,
                "description": "Objetivo individual en curso con progreso pendiente.",
            },
            {
                "name": "[DEMO] Citas de adquisición del periodo",
                "scope": "individual",
                "metric": "acquisition_appointments",
                "start_date": today - timedelta(days=90),
                "end_date": today + timedelta(days=15),
                "assignees": [marta],
                "target_mode": "partial",
                "target_gap": 2,
                "description": "Cuenta citas de adquisición programadas o completadas, excluyendo canceladas.",
            },
            {
                "name": "[DEMO] Cartera individual de encargos",
                "scope": "individual",
                "metric": "listings",
                "start_date": today - timedelta(days=90),
                "end_date": today + timedelta(days=30),
                "assignees": [operaciones],
                "target_mode": "achieved",
                "description": "Ejemplo de una meta individual de encargos ya alcanzada.",
            },
            {
                "name": "[DEMO] Encargos compartidos del equipo",
                "scope": "team",
                "metric": "listings",
                "start_date": today - timedelta(days=90),
                "end_date": today + timedelta(days=30),
                "assignees": demo_team,
                "target_mode": "partial",
                "target_gap": 5,
                "description": "Objetivo grupal en el que se puede revisar la aportación de cada agente.",
            },
            {
                "name": "[DEMO] Contactos captados por el equipo",
                "scope": "team",
                "metric": "contacts",
                "start_date": today - timedelta(days=90),
                "end_date": today + timedelta(days=30),
                "assignees": agents,
                "target_mode": "achieved",
                "description": "Meta compartida por todos los agentes y configurada como conseguida.",
            },
            {
                "name": "[DEMO] Pedidos del próximo mes",
                "scope": "team",
                "metric": "orders",
                "start_date": today + timedelta(days=7),
                "end_date": today + timedelta(days=37),
                "assignees": demo_team,
                "target_mode": "fixed",
                "target_count": 10,
                "description": "Objetivo futuro para comprobar el estado próximo y el progreso a cero.",
            },
            {
                "name": "[DEMO] Alquileres del periodo anterior",
                "scope": "individual",
                "metric": "rentals",
                "start_date": today - timedelta(days=90),
                "end_date": today - timedelta(days=1),
                "assignees": [operaciones],
                "target_mode": "partial",
                "target_gap": 2,
                "description": "Objetivo finalizado que no llegó a alcanzar la cantidad prevista.",
            },
            {
                "name": "[DEMO] Ventas históricas completadas",
                "scope": "individual",
                "metric": "sales",
                "start_date": today - timedelta(days=120),
                "end_date": today - timedelta(days=1),
                "assignees": [carlos],
                "target_mode": "achieved",
                "description": "Objetivo finalizado que muestra una meta histórica conseguida.",
            },
        ]

        created_count = 0
        for scenario in scenarios:
            assignees = scenario.pop("assignees")
            target_mode = scenario.pop("target_mode")
            target_gap = scenario.pop("target_gap", 0)
            fixed_target = scenario.pop("target_count", 1)
            description = f"{self.marker} {scenario.pop('description')}"
            goal, created = Goal.objects.update_or_create(
                name=scenario["name"],
                defaults={
                    **scenario,
                    "description": description,
                    "target_count": fixed_target,
                    "created_by": creator,
                },
            )
            goal.assignees.set(assignees)
            current = calculate_progress(goal)
            if target_mode == "achieved":
                target = max(current, 1)
            elif target_mode == "partial":
                target = current + target_gap
            else:
                target = fixed_target
            if goal.target_count != target:
                goal.target_count = target
                goal.save(update_fields=["target_count", "updated_at"])
            created_count += int(created)
            result = "conseguido" if current >= target else "en progreso"
            self.stdout.write(
                f"  {'Creado' if created else 'Actualizado'}: {goal.name} "
                f"({current}/{target}, {result})"
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Objetivos de prueba preparados: {len(scenarios)} "
                f"({created_count} nuevos, {len(scenarios) - created_count} actualizados)."
            )
        )
