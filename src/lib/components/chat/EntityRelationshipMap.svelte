<script lang="ts">
	import { onMount, onDestroy, createEventDispatcher } from 'svelte';

	export let history: any;

	const dispatch = createEventDispatcher();

	const ENTITY_TYPES = [
		'PERSON',
		'ORGANIZATION',
		'EMAIL_ADDRESS',
		'PHONE_NUMBER',
		'IBAN_CODE',
		'LOCATION',
		'ID'
	];

	const ENTITY_COLORS: Record<string, string> = {
		PERSON: '#3b82f6',
		EMAIL_ADDRESS: '#ef4444',
		ORGANIZATION: '#22c55e',
		LOCATION: '#a855f7',
		PHONE_NUMBER: '#f97316',
		IBAN_CODE: '#eab308',
		ID: '#ec4899'
	};

	const DEFAULT_COLOR = '#6b7280';
	const TOKEN_REGEX = /(PERSON|ORGANIZATION|EMAIL_ADDRESS|IBAN_CODE|PHONE_NUMBER|LOCATION|ID)_[a-f0-9]{8}/g;

	const SVG_W = 600;
	const SVG_H = 400;
	const RING_CX = 300;
	const RING_CY = 200;
	const RING_R = 150;
	const GROUP_R = 40;

	function buildNodes(messages: any[]): Map<string, { type: string; count: number }> {
		const nodes = new Map<string, { type: string; count: number }>();
		for (const msg of messages) {
			if (!msg.pseudonymized_prompt) continue;
			for (const match of msg.pseudonymized_prompt.matchAll(TOKEN_REGEX)) {
				const token = match[0];
				const type = token.split('_')[0];
				const existing = nodes.get(token);
				if (existing) {
					existing.count++;
				} else {
					nodes.set(token, { type, count: 1 });
				}
			}
		}
		return nodes;
	}

	function buildEdges(messages: any[]): Map<string, number> {
		const edges = new Map<string, number>();
		for (const msg of messages) {
			if (!msg.pseudonymized_prompt) continue;
			const tokens = [
				...new Set([...msg.pseudonymized_prompt.matchAll(TOKEN_REGEX)].map((m: any) => m[0]))
			] as string[];
			for (let i = 0; i < tokens.length; i++) {
				for (let j = i + 1; j < tokens.length; j++) {
					const key = [tokens[i], tokens[j]].sort().join('|');
					edges.set(key, (edges.get(key) ?? 0) + 1);
				}
			}
		}
		return edges;
	}

	function getNodePositions(
		nodes: Map<string, { type: string; count: number }>
	): Map<string, { x: number; y: number }> {
		const positions = new Map<string, { x: number; y: number }>();
		const byType = new Map<string, string[]>();

		for (const [token, data] of nodes) {
			if (!byType.has(data.type)) byType.set(data.type, []);
			byType.get(data.type)!.push(token);
		}

		const detectedTypes = [...byType.keys()];

		detectedTypes.forEach((type, typeIdx) => {
			const typeAngle = (typeIdx / detectedTypes.length) * 2 * Math.PI - Math.PI / 2;
			const cx = RING_CX + RING_R * Math.cos(typeAngle);
			const cy = RING_CY + RING_R * Math.sin(typeAngle);
			const tokens = byType.get(type)!;

			if (tokens.length === 1) {
				positions.set(tokens[0], { x: cx, y: cy });
			} else {
				const r = tokens.length > 6 ? GROUP_R * 0.6 : GROUP_R;
				tokens.forEach((token, i) => {
					const angle = (i / tokens.length) * 2 * Math.PI - Math.PI / 2;
					positions.set(token, {
						x: cx + r * Math.cos(angle),
						y: cy + r * Math.sin(angle)
					});
				});
			}
		});

		return positions;
	}

	$: messages = Object.values(history?.messages ?? {}) as any[];
	$: nodes = buildNodes(messages);
	$: edges = buildEdges(messages);
	$: nodePositions = getNodePositions(nodes);
	$: maxEdgeCount = edges.size > 0 ? Math.max(...edges.values()) : 1;
	$: activeTypes = ENTITY_TYPES.filter((t) => [...nodes.values()].some((n) => n.type === t));

	function edgeOpacity(count: number): number {
		return 0.3 + (count / maxEdgeCount) * 0.5;
	}

	function truncate(s: string, n = 12): string {
		return s.length > n ? s.slice(0, n) + '…' : s;
	}

	function getColor(type: string): string {
		return ENTITY_COLORS[type] ?? DEFAULT_COLOR;
	}

	let overlayEl: HTMLDivElement;

	function handleBackdrop(e: MouseEvent) {
		if (e.target === overlayEl) dispatch('close');
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape') dispatch('close');
	}

	onMount(() => {
		window.addEventListener('keydown', handleKeydown);
		console.warn('[GARNET MAP] mounted — nodes:', nodes.size, 'edges:', edges.size);
	});
	onDestroy(() => window.removeEventListener('keydown', handleKeydown));
</script>

<!-- svelte-ignore a11y-click-events-have-key-events -->
<!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
<div
	bind:this={overlayEl}
	on:click={handleBackdrop}
	role="dialog"
	aria-modal="true"
	aria-label="Entity Relationship Map"
	class="fixed inset-0 z-50 flex items-center justify-center bg-black/80"
>
	<div class="relative bg-white dark:bg-gray-900 rounded-xl shadow-2xl p-4 w-full max-w-[660px] mx-4">
		<div class="flex items-center justify-between mb-3">
			<span class="text-sm font-semibold text-gray-800 dark:text-gray-100">Entity Map</span>
			<button
				on:click={() => dispatch('close')}
				class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 text-lg leading-none px-1"
				aria-label="Close"
			>✕</button>
		</div>

		{#if nodes.size === 0}
			<p class="text-xs text-gray-400 text-center py-10">No entities detected yet.</p>
		{:else}
			<svg viewBox="0 0 {SVG_W} {SVG_H}" class="w-full h-auto">
				<!-- edges -->
				{#each [...edges.entries()] as [key, count]}
					{@const parts = key.split('|')}
					{@const posA = nodePositions.get(parts[0])}
					{@const posB = nodePositions.get(parts[1])}
					{#if posA && posB}
						<line
							x1={posA.x}
							y1={posA.y}
							x2={posB.x}
							y2={posB.y}
							stroke="#9ca3af"
							stroke-width="1.5"
							stroke-opacity={edgeOpacity(count)}
						/>
					{/if}
				{/each}

				<!-- nodes -->
				{#each [...nodes.entries()] as [token, data]}
					{@const pos = nodePositions.get(token)}
					{#if pos}
						<g>
							<circle cx={pos.x} cy={pos.y} r="14" fill={getColor(data.type)}>
								<title>{token} · seen in {data.count} message{data.count !== 1 ? 's' : ''}</title>
							</circle>
							<text
								x={pos.x}
								y={pos.y + 25}
								text-anchor="middle"
								font-size="9"
								fill="#9ca3af"
							>{truncate(token)}</text>
						</g>
					{/if}
				{/each}
			</svg>

			<!-- legend -->
			<div class="flex flex-wrap gap-x-4 gap-y-1 mt-1 justify-center">
				{#each activeTypes as type}
					<span class="flex items-center gap-1 text-[10px] text-gray-500 dark:text-gray-400">
						<span
							class="inline-block w-2.5 h-2.5 rounded-full shrink-0"
							style="background:{getColor(type)}"
						></span>
						{type}
					</span>
				{/each}
			</div>
		{/if}
	</div>
</div>
