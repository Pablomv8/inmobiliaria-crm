document.addEventListener("DOMContentLoaded", () => {
    const funnels = Array.from(document.querySelectorAll("[data-commercial-funnel]"));
    if (!funnels.length) return;

    const formatDate = value => {
        if (!value) return null;
        return new Intl.DateTimeFormat("es-ES").format(
            new Date(`${value}T00:00:00`),
        );
    };

    const updateFunnel = (container, data) => {
        container.querySelector("[data-funnel-closing-rate]").textContent =
            `${data.closing_rate}%`;

        const stageElements = container.querySelectorAll("[data-funnel-stage]");
        data.stages.forEach((stage, index) => {
            const element = stageElements[index];
            if (!element) return;
            const conversion = element.querySelector("[data-funnel-conversion]");
            const bar = element.querySelector("[data-funnel-bar]");

            element.href = stage.url;
            conversion.textContent = `${stage.conversion}% desde la fase anterior`;
            bar.classList.toggle("hidden", stage.count === 0);
            bar.style.width = `${stage.width}%`;
            bar.querySelector("[data-funnel-bar-value]").textContent =
                stage.width >= 18 ? stage.count : "";
            element.querySelector("[data-funnel-count]").textContent = stage.count;
        });

        const fromInput = container.querySelector("[data-funnel-from]");
        const toInput = container.querySelector("[data-funnel-to]");
        const clearButton = container.querySelector("[data-funnel-clear]");
        const periodMessage = container.querySelector("[data-funnel-period-message]");
        fromInput.value = data.period.from_value;
        toInput.value = data.period.to_value;
        clearButton.classList.toggle("hidden", !data.period.active);

        if (data.period.active) {
            const fromText = formatDate(data.period.from_value);
            const toText = formatDate(data.period.to_value);
            periodMessage.textContent = `Periodo aplicado: ${
                fromText ? `desde el ${fromText}` : "sin fecha inicial"
            } hasta ${toText ? `el ${toText}` : "sin fecha final"}.`;
            periodMessage.className = "mt-3 text-xs text-indigo-700";
        } else {
            periodMessage.textContent = "Sin filtro: se muestra todo el histórico comercial.";
            periodMessage.className = "mt-3 text-xs text-gray-500";
        }
    };

    const loadFunnel = async (container, dateFrom, dateTo) => {
        const params = new URLSearchParams({scope: container.dataset.funnelScope});
        if (container.dataset.funnelAgentId) {
            params.set("agent_id", container.dataset.funnelAgentId);
        }
        if (dateFrom) params.set("funnel_from", dateFrom);
        if (dateTo) params.set("funnel_to", dateTo);

        if (container.funnelRequestController) {
            container.funnelRequestController.abort();
        }
        container.funnelRequestController = new AbortController();
        const controller = container.funnelRequestController;
        container.setAttribute("aria-busy", "true");
        try {
            const response = await fetch(`${container.dataset.funnelUrl}?${params}`, {
                headers: {"X-Requested-With": "XMLHttpRequest"},
                signal: controller.signal,
            });
            if (!response.ok) throw new Error("No se pudo actualizar el embudo.");
            updateFunnel(container, await response.json());
            container.querySelector("[data-funnel-status]").textContent =
                "Embudo comercial actualizado.";
        } catch (error) {
            if (error.name !== "AbortError") {
                container.querySelector("[data-funnel-status]").textContent = error.message;
            }
        } finally {
            if (container.funnelRequestController === controller) {
                container.removeAttribute("aria-busy");
            }
        }
    };

    const refreshFunnels = (dateFrom, dateTo) => {
        if (dateFrom && dateTo && dateFrom > dateTo) {
            [dateFrom, dateTo] = [dateTo, dateFrom];
        }
        funnels.forEach(container => {
            container.querySelector("[data-funnel-from]").value = dateFrom;
            container.querySelector("[data-funnel-to]").value = dateTo;
            loadFunnel(container, dateFrom, dateTo);
        });

        const url = new URL(window.location.href);
        dateFrom
            ? url.searchParams.set("funnel_from", dateFrom)
            : url.searchParams.delete("funnel_from");
        dateTo
            ? url.searchParams.set("funnel_to", dateTo)
            : url.searchParams.delete("funnel_to");
        window.history.replaceState({}, "", `${url.pathname}${url.search}${url.hash}`);
    };

    funnels.forEach(container => {
        const form = container.querySelector("[data-funnel-form]");
        const fromInput = container.querySelector("[data-funnel-from]");
        const toInput = container.querySelector("[data-funnel-to]");
        const refresh = () => refreshFunnels(fromInput.value, toInput.value);

        form.addEventListener("submit", event => {
            event.preventDefault();
            refresh();
        });
        fromInput.addEventListener("change", refresh);
        toInput.addEventListener("change", refresh);
        container.querySelector("[data-funnel-clear]").addEventListener("click", () => {
            refreshFunnels("", "");
        });
    });
});
