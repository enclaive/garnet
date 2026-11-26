<script lang="ts">
	import { createEventDispatcher, getContext, onMount } from 'svelte';
	const dispatch = createEventDispatcher();
	const i18n = getContext('i18n');

	import XMark from '$lib/components/icons/XMark.svelte';
	import AdvancedParams from '../Settings/Advanced/AdvancedParams.svelte';
	import Valves from '$lib/components/chat/Controls/Valves.svelte';
	import FileItem from '$lib/components/common/FileItem.svelte';
	import Collapsible from '$lib/components/common/Collapsible.svelte';

	import { config, user, settings, privacyProxy } from '$lib/stores';
	export let models = [];
	export let chatFiles = [];
	export let params: Record<string, any> = {};
	export let onParamChange: (key: string, value: unknown) => void = () => {};
	export let embed = false;

	// Persist collapsible section open/close state
	const getOpen = (key: string, fallback = true): boolean => {
		const v = localStorage.getItem(`chatControls.${key}`);
		return v !== null ? v === 'true' : fallback;
	};
	const setOpen = (key: string) => (open: boolean) => {
		localStorage.setItem(`chatControls.${key}`, String(open));
	};

	let showFiles = getOpen('files');
	let showValves = getOpen('valves', false);
	let showSystemPrompt = getOpen('systemPrompt');
	let showAdvancedParams = false;
	let showGarnet = getOpen('garnet', true);

	// Garnet: per-entity screening toggles persisted in localStorage.
	const ENTITY_TYPES = [
		{ key: 'PERSON', label: 'Name / Person' },
		{ key: 'ORGANIZATION', label: 'Organization' },
		{ key: 'EMAIL_ADDRESS', label: 'Email' },
		{ key: 'IBAN_CODE', label: 'IBAN' },
		{ key: 'PHONE_NUMBER', label: 'Phone Number' },
		{ key: 'ID', label: 'ID' },
		{ key: 'LOCATION', label: 'Location' }
	];
	let entityToggles: Record<string, boolean> = {};
	let screeningSpeed = 0;

	onMount(() => {
		const saved = localStorage.getItem('garnet_entity_toggles');
		if (saved) {
			entityToggles = JSON.parse(saved);
		} else {
			ENTITY_TYPES.forEach((e) => (entityToggles[e.key] = true));
			localStorage.setItem('garnet_entity_toggles', JSON.stringify(entityToggles));
		}
		screeningSpeed = parseInt(localStorage.getItem('garnet_screening_speed') || '2000');
	});

	function onEntityChange(key: string, value: string) {
		entityToggles[key] = value === 'on';
		localStorage.setItem('garnet_entity_toggles', JSON.stringify(entityToggles));
		entityToggles = { ...entityToggles };
	}

	function onSpeedChange() {
		localStorage.setItem('garnet_screening_speed', String(screeningSpeed));
	}

	const compactSectionButtonClass =
		'w-full py-1 text-xs font-normal text-base-500 hover:text-base-900 dark:text-base-400 dark:hover:text-base-100 transition cursor-pointer select-none';
	const systemPromptTextareaClass =
		'w-full resize-vertical rounded-lg border border-base-100/50 bg-base-50/40 px-2 py-1.5 text-xs text-base-700 outline-hidden transition-colors placeholder:text-base-300 focus:border-blue-400 dark:border-base-0/[0.04] dark:bg-base-0/[0.03] dark:text-base-300 dark:placeholder:text-base-700 dark:focus:border-blue-500';
	const compactSystemPromptTextareaClass =
		'w-full resize-vertical appearance-none bg-transparent py-1 text-xs outline-hidden focus:bg-transparent disabled:bg-transparent';
</script>

<div class=" dark:text-base-0">
	{#if !embed}
		<div class=" flex items-center justify-between dark:text-base-100 mb-2">
			<div class=" text-md self-center">{$i18n.t('Controls')}</div>
			<button
				class="self-center"
				aria-label={$i18n.t('Close chat controls')}
				on:click={() => {
					dispatch('close');
				}}
			>
				<XMark className="size-3.5" />
			</button>
		</div>
	{/if}

	{#if $user?.role === 'admin' || ($user?.permissions.chat?.controls ?? true)}
		<div class="space-y-1 dark:text-base-200 text-sm py-0.5 px-0.5">
			{#if chatFiles.length > 0}
				<Collapsible
					title={$i18n.t('Files')}
					bind:open={showFiles}
					onChange={setOpen('files')}
					buttonClassName={compactSectionButtonClass}
					chevronClassName="size-2.5"
					chevronStrokeWidth="2"
				>
					<div class="flex flex-col gap-1 pt-1 pb-1 text-xs" slot="content">
						{#each chatFiles as file, fileIdx}
							<FileItem
								className="w-full"
								item={file}
								edit={true}
								url={file?.url ? file.url : null}
								name={file.name}
								type={file.type}
								size={file?.size}
								dismissible={true}
								small={true}
								on:dismiss={() => {
									// Remove the file from the chatFiles array

									chatFiles.splice(fileIdx, 1);
									chatFiles = chatFiles;
								}}
								on:click={() => {
									console.log(file);
								}}
							/>
						{/each}
					</div>
				</Collapsible>
			{/if}

			{#if ($config?.features?.enable_tools || $config?.features?.enable_functions) && ($user?.role === 'admin' || ($user?.permissions.chat?.valves ?? true))}
				<Collapsible
					bind:open={showValves}
					onChange={setOpen('valves')}
					title={$i18n.t('Valves')}
					buttonClassName={compactSectionButtonClass}
					chevronClassName="size-2.5"
					chevronStrokeWidth="2"
				>
					<div class="pt-1 pb-1 text-xs" slot="content">
						<Valves show={showValves} />
					</div>
				</Collapsible>
			{/if}

			{#if $user?.role === 'admin' || ($user?.permissions.chat?.system_prompt ?? true)}
				<Collapsible
					title={$i18n.t('System Prompt')}
					bind:open={showSystemPrompt}
					onChange={setOpen('systemPrompt')}
					buttonClassName={compactSectionButtonClass}
					chevronClassName="size-2.5"
					chevronStrokeWidth="2"
				>
					<div class="pt-1 pb-1" slot="content">
						<textarea
							bind:value={params.system}
							on:change={() => onParamChange('system', params.system)}
							class={($settings?.highContrastMode ?? false)
								? systemPromptTextareaClass
								: compactSystemPromptTextareaClass}
							rows="3"
							placeholder={$i18n.t('Enter system prompt')}
							aria-label={$i18n.t('System Prompt')}
						/>
					</div>
				</Collapsible>
			{/if}

			{#if $user?.role === 'admin' || ($user?.permissions.chat?.params ?? true)}
				<Collapsible
					title={$i18n.t('Advanced Params')}
					bind:open={showAdvancedParams}
					buttonClassName={compactSectionButtonClass}
					chevronClassName="size-2.5"
					chevronStrokeWidth="2"
				>
					<div
						class="pt-1 pb-1 text-xs [&_label]:truncate [&_label]:pb-1 [&_label]:-mb-1 [&_label+div]:shrink-0 [&_.inline-tooltip_label]:cursor-help!"
						slot="content"
					>
						<div class="[&>div]:space-y-0 [&>div>div]:py-0">
							<AdvancedParams
								admin={$user?.role === 'admin'}
								custom={true}
								bind:params
								{onParamChange}
							/>
						</div>
					</div>
				</Collapsible>
			{/if}

			<Collapsible
				title={$i18n.t('Garnet')}
				bind:open={showGarnet}
				onChange={setOpen('garnet')}
				buttonClassName={compactSectionButtonClass}
				chevronClassName="size-2.5"
				chevronStrokeWidth="2"
			>
				<div class="pt-1 pb-1 text-xs" slot="content">
					<div class="py-0.5 flex w-full justify-between items-center">
						<div class="self-center">{$i18n.t('Privacy Proxy')}</div>
						<select
							value={$privacyProxy ? 'on' : 'off'}
							on:change={(e) => privacyProxy.set(e.currentTarget.value === 'on')}
							class="p-1 px-3 text-xs rounded-sm transition bg-base-50 text-base-700 hover:bg-base-100 dark:bg-base-900 dark:text-base-200 dark:hover:bg-base-800 border border-base-100 dark:border-base-800 focus:outline-none cursor-pointer"
						>
							<option value="on">{$i18n.t('On')}</option>
							<option value="off">{$i18n.t('Off')}</option>
						</select>
					</div>

					<div class="mt-2 pt-2 border-t border-base-100 dark:border-base-800 flex flex-col gap-0.5">
						{#each ENTITY_TYPES as entity}
							<div class="py-0.5 flex w-full justify-between items-center">
								<div class="self-center">{entity.label}</div>
								<select
									value={entityToggles[entity.key] ? 'on' : 'off'}
									on:change={(e) => onEntityChange(entity.key, e.currentTarget.value)}
									class="p-1 px-3 text-xs rounded-sm transition bg-base-50 text-base-700 hover:bg-base-100 dark:bg-base-900 dark:text-base-200 dark:hover:bg-base-800 border border-base-100 dark:border-base-800 focus:outline-none cursor-pointer"
								>
									<option value="on">{$i18n.t('On')}</option>
									<option value="off">{$i18n.t('Off')}</option>
								</select>
							</div>
						{/each}
					</div>

					<div
						class="py-0.5 flex w-full justify-between items-center mt-2 pt-2 border-t border-base-100 dark:border-base-800"
					>
						<div class="self-center">{$i18n.t('Screening Speed')}</div>
						<input
							type="number"
							min="0"
							step="500"
							bind:value={screeningSpeed}
							on:change={onSpeedChange}
							class="p-1 px-2 text-xs w-24 rounded-sm bg-base-50 text-base-700 dark:bg-base-900 dark:text-base-200 border border-base-100 dark:border-base-800 focus:outline-none"
						/>
					</div>
				</div>
			</Collapsible>
		</div>
	{/if}
</div>
