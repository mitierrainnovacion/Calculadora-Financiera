Actúa como un ingeniero de software financiero (fintech) especializado en modelación de proyectos inmobiliarios.
Debes implementar el cálculo correcto de la TIR (Tasa Interna de Retorno) para un proyecto de desarrollo horizontal (fraccionamiento y venta de lotes) dentro de una calculadora financiera.

1. Alcance del cálculo
	•	El cálculo se realiza a nivel proyecto completo.
	•	El horizonte temporal es mensual.
	•	El resultado principal es:
	•	TIR mensual
	•	TIR anual equivalente:
>     TIR_{anual} = (1 + TIR_{mensual})^{12} - 1
>

⸻

2. Estructura del flujo de caja

Implementa un array ordenado de flujos de caja, donde:

cashFlows[0] = flujo en mes 0
cashFlows[1] = flujo en mes 1
...
cashFlows[n] = flujo en mes n

2.1 Flujos negativos (egresos)
Deben registrarse con signo negativo e incluir:
	•	Compra del terreno (precio + impuestos + gastos notariales) en mes 0.
	•	Costos de desarrollo y urbanización distribuidos mensualmente.
	•	Gastos administrativos.
	•	Gastos de comercialización.
	•	Costos financieros (si aplica).

2.2 Flujos positivos (ingresos)
Deben registrarse con signo positivo e incluir:
	•	Ingresos por venta de lotes:
	•	lotesVendidosMes × precioPromedioLote
	•	Considerar:
	•	Ritmo de absorción mensual.
	•	Preventas.
	•	Ventas financiadas (ingresos parciales y cuotas).
	•	Descontar:
	•	Comisiones de venta.
	•	Impuestos aplicables.

⸻

3. Reglas de consistencia del flujo

Implementa validaciones:
	•	El flujo debe contener al menos un valor negativo y uno positivo.
	•	El flujo debe estar cronológicamente ordenado.
	•	No se permite calcular TIR si la suma de flujos positivos es ≤ suma de flujos negativos.
	•	El período del flujo es siempre mensual, sin conversión automática.

⸻

4. Cálculo matemático de la TIR

Implementa una función calculateIRR(cashFlows) que:
	•	Encuentre la tasa r tal que:
>   \sum_{t=0}^{n} \frac{cashFlows[t]}{(1 + r)^t} = 0
>
	•	Use un método iterativo:
	•	Newton-Raphson o
	•	Bisección (preferido por estabilidad).
	•	Condiciones:
	•	Tolerancia: 1e-6
	•	Máximo de iteraciones: 1000

⸻

5. Manejo de casos especiales
	•	Si no converge → devolver error controlado.
	•	Si existen múltiples cambios de signo → advertir posible multiplicidad de TIR.
	•	Si la TIR es negativa → devolver valor negativo sin ajuste.

⸻

6. Resultados esperados

El módulo debe devolver:

{
  "tir_mensual": number,
  "tir_anual_equivalente": number,
  "cash_flows": number[],
  "converged": boolean
}


⸻

7. Supuestos explícitos
	•	No incluir valor residual salvo que se indique explícitamente.
	•	No suavizar ni agrupar flujos.
	•	No convertir períodos (mensual → anual) antes del cálculo.

⸻

8. Objetivo final

El cálculo debe ser financieramente correcto, determinístico, reproducible y alineado con estándares de evaluación de proyectos inmobiliarios.

Implementa el código necesario en el lenguaje del proyecto y documenta brevemente las decisiones clave.

⸻