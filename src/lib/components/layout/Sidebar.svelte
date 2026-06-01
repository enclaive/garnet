<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { v4 as uuidv4 } from 'uuid';

	import { goto } from '$app/navigation';
	import {
		user,
		chats,
		settings,
		showSettings,
		chatId,
		tags,
		folders as _folders,
		showSidebar,
		showSearch,
		mobile,
		showArchivedChats,
		pinnedChats,
		scrollPaginationEnabled,
		currentChatPage,
		temporaryChatEnabled,
		channels,
		socket,
		config,
		isApp,
		models,
		selectedFolder,
		WEBUI_NAME,
		sidebarWidth,
		activeChatIds
	} from '$lib/stores';
	import { onMount, getContext, tick, onDestroy } from 'svelte';

	const i18n = getContext('i18n');

	import {
		getChatList,
		getAllTags,
		getPinnedChatList,
		toggleChatPinnedStatusById,
		getChatById,
		updateChatFolderIdById,
		importChats
	} from '$lib/apis/chats';
	import { createNewFolder, getFolders, updateFolderParentIdById } from '$lib/apis/folders';
	import { checkActiveChats } from '$lib/apis/tasks';
	import { WEBUI_API_BASE_URL, WEBUI_BASE_URL } from '$lib/constants';

	import ArchivedChatsModal from './ArchivedChatsModal.svelte';
	import UserMenu from './Sidebar/UserMenu.svelte';
	import ChatItem from './Sidebar/ChatItem.svelte';
	import Spinner from '../common/Spinner.svelte';
	import Loader from '../common/Loader.svelte';
	import Folder from '../common/Folder.svelte';
	import Tooltip from '../common/Tooltip.svelte';
	import Folders from './Sidebar/Folders.svelte';
	import { getChannels, createNewChannel } from '$lib/apis/channels';
	import ChannelModal from './Sidebar/ChannelModal.svelte';
	import ChannelItem from './Sidebar/ChannelItem.svelte';
	import PencilSquare from '../icons/PencilSquare.svelte';
	import Search from '../icons/Search.svelte';
	import SearchModal from './SearchModal.svelte';
	import FolderModal from './Sidebar/Folders/FolderModal.svelte';
	import Sidebar from '../icons/Sidebar.svelte';
	import PinnedModelList from './Sidebar/PinnedModelList.svelte';
	import Note from '../icons/Note.svelte';
	import { slide } from 'svelte/transition';
	import HotkeyHint from '../common/HotkeyHint.svelte';

	const BREAKPOINT = 768;

	let scrollTop = 0;

	let navElement;
	let shiftKey = false;

	let selectedChatId = null;
	let showCreateChannel = false;

	// Pagination variables
	let chatListLoading = false;
	let allChatsLoaded = false;

	let showCreateFolderModal = false;

	let pinnedModels = [];

	let showPinnedModels = false;
	let showChannels = false;
	let showFolders = false;

	let folders = {};
	let folderRegistry = {};

	let newFolderId = null;

	$: if ($selectedFolder) {
		initFolders();
	}

	const initFolders = async () => {
		if ($config?.features?.enable_folders === false) {
			return;
		}

		const folderList = await getFolders(localStorage.token).catch((error) => {
			return [];
		});
		_folders.set(folderList.sort((a, b) => b.updated_at - a.updated_at));

		folders = {};

		// First pass: Initialize all folder entries
		for (const folder of folderList) {
			// Ensure folder is added to folders with its data
			folders[folder.id] = { ...(folders[folder.id] || {}), ...folder };

			if (newFolderId && folder.id === newFolderId) {
				folders[folder.id].new = true;
				newFolderId = null;
			}
		}

		// Second pass: Tie child folders to their parents
		for (const folder of folderList) {
			if (folder.parent_id) {
				// Ensure the parent folder is initialized if it doesn't exist
				if (!folders[folder.parent_id]) {
					folders[folder.parent_id] = {}; // Create a placeholder if not already present
				}

				// Initialize childrenIds array if it doesn't exist and add the current folder id
				folders[folder.parent_id].childrenIds = folders[folder.parent_id].childrenIds
					? [...folders[folder.parent_id].childrenIds, folder.id]
					: [folder.id];

				// Sort the children by updated_at field
				folders[folder.parent_id].childrenIds.sort((a, b) => {
					return folders[b].updated_at - folders[a].updated_at;
				});
			}
		}
	};

	const createFolder = async ({ name, data, parent_id }) => {
		name = name?.trim();
		if (!name) {
			toast.error($i18n.t('Folder name cannot be empty.'));
			return;
		}

		// Check for duplicate names in the same parent
		const siblings = Object.values(folders).filter((folder) => folder.parent_id === parent_id);
		if (siblings.find((folder) => folder.name.toLowerCase() === name.toLowerCase())) {
			// If a folder with the same name already exists, append a number to the name
			let i = 1;
			while (
				siblings.find((folder) => folder.name.toLowerCase() === `${name} ${i}`.toLowerCase())
			) {
				i++;
			}

			name = `${name} ${i}`;
		}

		// Add a dummy folder to the list to show the user that the folder is being created
		const tempId = uuidv4();
		folders = {
			...folders,
			[tempId]: {
				id: tempId,
				name: name,
				parent_id: parent_id,
				created_at: Date.now(),
				updated_at: Date.now()
			}
		};

		const res = await createNewFolder(localStorage.token, {
			name,
			data,
			parent_id
		}).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			// newFolderId = res.id;
			await initFolders();
			showFolders = true;
		}
	};

	const initChannels = async () => {
		// default (none), group, dm type
		const res = await getChannels(localStorage.token).catch((error) => {
			return null;
		});

		if (res) {
			await channels.set(
				res.sort(
					(a, b) =>
						['', null, 'group', 'dm'].indexOf(a.type) - ['', null, 'group', 'dm'].indexOf(b.type)
				)
			);
		}
	};

	const initChatList = async () => {
		// Reset pagination variables
		console.log('initChatList');
		currentChatPage.set(1);
		allChatsLoaded = false;
		scrollPaginationEnabled.set(false);

		initFolders();
		await Promise.all([
			await (async () => {
				console.log('Init tags');
				const _tags = await getAllTags(localStorage.token);
				tags.set(_tags);
			})(),
			await (async () => {
				console.log('Init pinned chats');
				const _pinnedChats = await getPinnedChatList(localStorage.token);
				pinnedChats.set(_pinnedChats);
			})(),
			await (async () => {
				console.log('Init chat list');
				const _chats = await getChatList(localStorage.token, $currentChatPage);
				await chats.set(_chats);
			})()
		]);

		// Enable pagination
		scrollPaginationEnabled.set(true);
	};

	const loadMoreChats = async () => {
		chatListLoading = true;

		currentChatPage.set($currentChatPage + 1);

		let newChatList = [];

		newChatList = await getChatList(localStorage.token, $currentChatPage);

		// once the bottom of the list has been reached (no results) there is no need to continue querying
		allChatsLoaded = newChatList.length === 0;
		const existingIds = new Set(($chats ?? []).map((c) => c.id));
		const uniqueNewChats = newChatList.filter((c) => !existingIds.has(c.id));
		await chats.set([...($chats ? $chats : []), ...uniqueNewChats]);

		chatListLoading = false;
	};

	const importChatHandler = async (items, pinned = false, folderId = null) => {
		console.log('importChatHandler', items, pinned, folderId);
		for (const item of items) {
			console.log(item);
			if (item.chat) {
				await importChats(localStorage.token, [
					{
						chat: item.chat,
						meta: item?.meta ?? {},
						pinned: pinned,
						folder_id: folderId,
						created_at: item?.created_at ?? null,
						updated_at: item?.updated_at ?? null
					}
				]);
			}
		}

		initChatList();
	};

	const inputFilesHandler = async (files) => {
		console.log(files);

		for (const file of files) {
			const reader = new FileReader();
			reader.onload = async (e) => {
				const content = e.target.result;

				try {
					const chatItems = JSON.parse(content);
					importChatHandler(chatItems);
				} catch {
					toast.error($i18n.t(`Invalid file format.`));
				}
			};

			reader.readAsText(file);
		}
	};

	const tagEventHandler = async (type, tagName, chatId) => {
		console.log(type, tagName, chatId);
		if (type === 'delete') {
			initChatList();
		} else if (type === 'add') {
			initChatList();
		}
	};

	let draggedOver = false;

	const onDragOver = (e) => {
		e.preventDefault();

		// Check if a file is being draggedOver.
		if (e.dataTransfer?.types?.includes('Files')) {
			draggedOver = true;
		} else {
			draggedOver = false;
		}
	};

	const onDragLeave = () => {
		draggedOver = false;
	};

	const onDrop = async (e) => {
		e.preventDefault();
		console.log(e); // Log the drop event

		// Perform file drop check and handle it accordingly
		if (e.dataTransfer?.files) {
			const inputFiles = Array.from(e.dataTransfer?.files);

			if (inputFiles && inputFiles.length > 0) {
				console.log(inputFiles); // Log the dropped files
				inputFilesHandler(inputFiles); // Handle the dropped files
			}
		}

		draggedOver = false; // Reset draggedOver status after drop
	};

	let touchstart;
	let touchend;

	function checkDirection() {
		const screenWidth = window.innerWidth;
		const swipeDistance = Math.abs(touchend.screenX - touchstart.screenX);
		if (touchstart.clientX < 40 && swipeDistance >= screenWidth / 8) {
			if (touchend.screenX < touchstart.screenX) {
				showSidebar.set(false);
			}
			if (touchend.screenX > touchstart.screenX) {
				showSidebar.set(true);
			}
		}
	}

	const onTouchStart = (e) => {
		touchstart = e.changedTouches[0];
		console.log(touchstart.clientX);
	};

	const onTouchEnd = (e) => {
		touchend = e.changedTouches[0];
		checkDirection();
	};

	const onKeyDown = (e) => {
		if (e.key === 'Shift') {
			shiftKey = true;
		}
	};

	const onKeyUp = (e) => {
		if (e.key === 'Shift') {
			shiftKey = false;
		}
	};

	const onFocus = () => {};

	const onBlur = () => {
		shiftKey = false;
		selectedChatId = null;
	};

	const MIN_WIDTH = 220;
	const MAX_WIDTH = 480;

	let isResizing = false;

	let startWidth = 0;
	let startClientX = 0;

	const resizeStartHandler = (e: MouseEvent) => {
		if ($mobile) return;
		isResizing = true;

		startClientX = e.clientX;
		startWidth = $sidebarWidth ?? 260;

		document.body.style.userSelect = 'none';
	};

	const resizeEndHandler = () => {
		if (!isResizing) return;
		isResizing = false;

		document.body.style.userSelect = '';
		localStorage.setItem('sidebarWidth', String($sidebarWidth));
	};

	const resizeSidebarHandler = (endClientX) => {
		const dx = endClientX - startClientX;
		const newSidebarWidth = Math.min(MAX_WIDTH, Math.max(MIN_WIDTH, startWidth + dx));

		sidebarWidth.set(newSidebarWidth);
		document.documentElement.style.setProperty('--sidebar-width', `${newSidebarWidth}px`);
	};

	onMount(() => {
		try {
			const width = Number(localStorage.getItem('sidebarWidth'));
			if (!Number.isNaN(width) && width >= MIN_WIDTH && width <= MAX_WIDTH) {
				sidebarWidth.set(width);
			}
		} catch {}

		document.documentElement.style.setProperty('--sidebar-width', `${$sidebarWidth}px`);
		sidebarWidth.subscribe((w) => {
			document.documentElement.style.setProperty('--sidebar-width', `${w}px`);
		});

		showSidebar.set(!$mobile ? localStorage.sidebar === 'true' : false);

		const unsubscribers = [
			mobile.subscribe((value) => {
				if ($showSidebar && value) {
					showSidebar.set(false);
				}

				if ($showSidebar && !value) {
					const navElement = document.getElementsByTagName('nav')[0];
					if (navElement) {
						navElement.style['-webkit-app-region'] = 'drag';
					}
				}
			}),
			showSidebar.subscribe(async (value) => {
				localStorage.sidebar = value;

				// nav element is not available on the first render
				const navElement = document.getElementsByTagName('nav')[0];

				if (navElement) {
					if ($mobile) {
						if (!value) {
							navElement.style['-webkit-app-region'] = 'drag';
						} else {
							navElement.style['-webkit-app-region'] = 'no-drag';
						}
					} else {
						navElement.style['-webkit-app-region'] = 'drag';
					}
				}

				if (value) {
					// Only fetch channels if the feature is enabled and user has permission
					if (
						$config?.features?.enable_channels &&
						($user?.role === 'admin' || ($user?.permissions?.features?.channels ?? true))
					) {
						await initChannels();
					}
					await initChatList();

					// Check which chats have active tasks
					const allChatIds = [...$chats.map((c) => c.id), ...$pinnedChats.map((c) => c.id)];
					if (allChatIds.length > 0) {
						try {
							const res = await checkActiveChats(localStorage.token, allChatIds);
							activeChatIds.set(new Set(res.active_chat_ids || []));
						} catch (e) {
							console.debug('Failed to check active chats:', e);
						}
					}
				}
			}),
			settings.subscribe((value) => {
				if (pinnedModels != value?.pinnedModels ?? []) {
					pinnedModels = value?.pinnedModels ?? [];
					showPinnedModels = pinnedModels.length > 0;
				}
			})
		];

		window.addEventListener('keydown', onKeyDown);
		window.addEventListener('keyup', onKeyUp);

		window.addEventListener('touchstart', onTouchStart);
		window.addEventListener('touchend', onTouchEnd);

		window.addEventListener('focus', onFocus);
		window.addEventListener('blur', onBlur);

		const dropZone = document.getElementById('sidebar');
		if (dropZone) {
			dropZone.addEventListener('dragover', onDragOver);
			dropZone.addEventListener('drop', onDrop);
			dropZone.addEventListener('dragleave', onDragLeave);
		}

		const socketInstance = $socket;
		socketInstance?.on('events', chatActiveEventHandler);

		return () => {
			unsubscribers.forEach((unsubscriber) => unsubscriber());

			window.removeEventListener('keydown', onKeyDown);
			window.removeEventListener('keyup', onKeyUp);

			window.removeEventListener('touchstart', onTouchStart);
			window.removeEventListener('touchend', onTouchEnd);

			window.removeEventListener('focus', onFocus);
			window.removeEventListener('blur', onBlur);

			if (dropZone) {
				dropZone.removeEventListener('dragover', onDragOver);
				dropZone.removeEventListener('drop', onDrop);
				dropZone.removeEventListener('dragleave', onDragLeave);
			}

			socketInstance?.off('events', chatActiveEventHandler);
		};
	});

	// Handler for chat:active events (defined outside onMount for proper cleanup)
	const chatActiveEventHandler = (event: {
		chat_id: string;
		message_id: string;
		data: { type: string; data: any };
	}) => {
		if (event.data?.type === 'chat:active') {
			const { active } = event.data.data;
			activeChatIds.update((ids) => {
				const newSet = new Set(ids);
				if (active) {
					newSet.add(event.chat_id);
				} else {
					newSet.delete(event.chat_id);
				}
				return newSet;
			});
		}
	};

	const newChatHandler = async () => {
		selectedChatId = null;
		selectedFolder.set(null);

		if ($user?.role !== 'admin' && $user?.permissions?.chat?.temporary_enforced) {
			await temporaryChatEnabled.set(true);
		} else {
			await temporaryChatEnabled.set(false);
		}

		setTimeout(() => {
			if ($mobile) {
				showSidebar.set(false);
			}
		}, 0);
	};

	const itemClickHandler = async () => {
		selectedChatId = null;
		chatId.set('');

		if ($mobile) {
			showSidebar.set(false);
		}

		await tick();
	};

	const isWindows = /Windows/i.test(navigator.userAgent);
</script>

<ArchivedChatsModal
	bind:show={$showArchivedChats}
	onUpdate={async () => {
		await initChatList();
	}}
	onDelete={(id) => {
		if ($chatId === id) {
			goto('/');
			chatId.set('');
		}
	}}
/>

<ChannelModal
	bind:show={showCreateChannel}
	onSubmit={async (payload: any) => {
		let { type, name, is_private, access_grants, group_ids, user_ids } = payload ?? {};
		name = name?.trim();

		if (type === 'dm') {
			if (!user_ids || user_ids.length === 0) {
				toast.error($i18n.t('Please select at least one user for Direct Message channel.'));
				return;
			}
		} else {
			if (!name) {
				toast.error($i18n.t('Channel name cannot be empty.'));
				return;
			}
		}

		const res = await createNewChannel(localStorage.token, {
			type: type,
			name: name,
			is_private: is_private,
			access_grants: access_grants,
			group_ids: group_ids,
			user_ids: user_ids
		}).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			$socket.emit('join-channels', { auth: { token: $user?.token } });
			await initChannels();
			showCreateChannel = false;
			showChannels = true;
			goto(`/channels/${res.id}`);
		}
	}}
/>

<FolderModal
	bind:show={showCreateFolderModal}
	onSubmit={async (folder) => {
		await createFolder(folder);
		showCreateFolderModal = false;
	}}
/>

<!-- svelte-ignore a11y-no-static-element-interactions -->

{#if $showSidebar}
	<div
		class=" {$isApp
			? ' ml-[4.5rem] md:ml-0'
			: ''} fixed md:hidden z-40 top-0 right-0 left-0 bottom-0 bg-black/60 w-full min-h-screen h-screen flex justify-center overflow-hidden overscroll-contain"
		on:mousedown={() => {
			showSidebar.set(!$showSidebar);
		}}
	/>
{/if}

<SearchModal
	bind:show={$showSearch}
	onClose={() => {
		if ($mobile) {
			showSidebar.set(false);
		}
	}}
/>

<button
	id="sidebar-new-chat-button"
	class="hidden"
	on:click={() => {
		goto('/');
		newChatHandler();
	}}
/>

<svelte:window
	on:mousemove={(e) => {
		if (!isResizing) return;
		resizeSidebarHandler(e.clientX);
	}}
	on:mouseup={() => {
		resizeEndHandler();
	}}
/>

{#if !$mobile && !$showSidebar}
	<div
		class=" pt-[7px] pb-2 px-2 flex flex-col justify-between text-black dark:text-white hover:bg-gray-50/30 dark:hover:bg-gray-950/30 h-full z-10 transition-all border-e-[0.5px] border-gray-50 dark:border-gray-850/30"
		id="sidebar"
	>
		<button
			class="flex flex-col flex-1 {isWindows ? 'cursor-pointer' : 'cursor-[e-resize]'}"
			on:click={async () => {
				showSidebar.set(!$showSidebar);
			}}
		>
			<div class="pb-1.5">
				<Tooltip
					content={$showSidebar ? $i18n.t('Close Sidebar') : $i18n.t('Open Sidebar')}
					placement="right"
				>
					<button
						class="flex rounded-xl hover:bg-gray-100 dark:hover:bg-gray-850 transition group {isWindows
							? 'cursor-pointer'
							: 'cursor-[e-resize]'}"
						aria-label={$showSidebar ? $i18n.t('Close Sidebar') : $i18n.t('Open Sidebar')}
					>
						<div class=" self-center flex items-center justify-center size-9">
							<div class="sidebar-new-chat-icon size-6 group-hover:hidden rounded-full overflow-hidden flex-shrink-0">
								<img src="data:image/jpeg;base64,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" alt="Garnet" class="size-6 object-cover rounded-full" />
							</div>

							<Sidebar className="size-5 hidden group-hover:flex" />
						</div>
					</button>
				</Tooltip>
			</div>

			<div class="-mt-[0.5px]">
				<div class="">
					<Tooltip content={$i18n.t('New Chat')} placement="right">
						<a
							class=" cursor-pointer flex rounded-xl hover:bg-gray-100 dark:hover:bg-gray-850 transition group"
							href="/"
							draggable="false"
							on:click={async (e) => {
								e.stopImmediatePropagation();
								e.preventDefault();

								goto('/');
								newChatHandler();
							}}
							aria-label={$i18n.t('New Chat')}
						>
							<div class=" self-center flex items-center justify-center size-9">
								<PencilSquare className="size-4.5" />
							</div>
						</a>
					</Tooltip>
				</div>

				<div>
					<Tooltip content={$i18n.t('Search')} placement="right">
						<button
							class=" cursor-pointer flex rounded-xl hover:bg-gray-100 dark:hover:bg-gray-850 transition group"
							on:click={(e) => {
								e.stopImmediatePropagation();
								e.preventDefault();

								showSearch.set(true);
							}}
							draggable="false"
							aria-label={$i18n.t('Search')}
						>
							<div class=" self-center flex items-center justify-center size-9">
								<Search className="size-4.5" />
							</div>
						</button>
					</Tooltip>
				</div>

				{#if ($config?.features?.enable_notes ?? false) && ($user?.role === 'admin' || ($user?.permissions?.features?.notes ?? true))}
					<div class="">
						<Tooltip content={$i18n.t('Notes')} placement="right">
							<a
								class=" cursor-pointer flex rounded-xl hover:bg-gray-100 dark:hover:bg-gray-850 transition group"
								href="/notes"
								on:click={async (e) => {
									e.stopImmediatePropagation();
									e.preventDefault();

									goto('/notes');
									itemClickHandler();
								}}
								draggable="false"
								aria-label={$i18n.t('Notes')}
							>
								<div class=" self-center flex items-center justify-center size-9">
									<Note className="size-4.5" />
								</div>
							</a>
						</Tooltip>
					</div>
				{/if}

				{#if $user?.role === 'admin' || $user?.permissions?.workspace?.models || $user?.permissions?.workspace?.knowledge || $user?.permissions?.workspace?.prompts || $user?.permissions?.workspace?.tools}
					<div class="">
						<Tooltip content={$i18n.t('Workspace')} placement="right">
							<a
								class=" cursor-pointer flex rounded-xl hover:bg-gray-100 dark:hover:bg-gray-850 transition group"
								href="/workspace"
								on:click={async (e) => {
									e.stopImmediatePropagation();
									e.preventDefault();

									goto('/workspace');
									itemClickHandler();
								}}
								aria-label={$i18n.t('Workspace')}
								draggable="false"
							>
								<div class=" self-center flex items-center justify-center size-9">
									<svg
										xmlns="http://www.w3.org/2000/svg"
										fill="none"
										viewBox="0 0 24 24"
										stroke-width="1.5"
										stroke="currentColor"
										class="size-4.5"
									>
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											d="M13.5 16.875h3.375m0 0h3.375m-3.375 0V13.5m0 3.375v3.375M6 10.5h2.25a2.25 2.25 0 0 0 2.25-2.25V6a2.25 2.25 0 0 0-2.25-2.25H6A2.25 2.25 0 0 0 3.75 6v2.25A2.25 2.25 0 0 0 6 10.5Zm0 9.75h2.25A2.25 2.25 0 0 0 10.5 18v-2.25a2.25 2.25 0 0 0-2.25-2.25H6a2.25 2.25 0 0 0-2.25 2.25V18A2.25 2.25 0 0 0 6 20.25Zm9.75-9.75H18a2.25 2.25 0 0 0 2.25-2.25V6A2.25 2.25 0 0 0 18 3.75h-2.25A2.25 2.25 0 0 0 13.5 6v2.25a2.25 2.25 0 0 0 2.25 2.25Z"
										/>
									</svg>
								</div>
							</a>
						</Tooltip>
					</div>
				{/if}
			</div>
		</button>

		<div>
			<div>
				<div class=" py-2 flex justify-center items-center">
					{#if $user !== undefined && $user !== null}
						<UserMenu
							role={$user?.role}
							profile={$config?.features?.enable_user_status ?? true}
							showActiveUsers={false}
							on:show={(e) => {
								if (e.detail === 'archived-chat') {
									showArchivedChats.set(true);
								}
							}}
						>
							<div
								class=" cursor-pointer flex rounded-xl hover:bg-gray-100 dark:hover:bg-gray-850 transition group"
							>
								<div class="self-center relative">
									<img
										src={`${WEBUI_API_BASE_URL}/users/${$user?.id}/profile/image`}
										class=" size-7 object-cover rounded-full"
										alt={$i18n.t('Open User Profile Menu')}
										aria-label={$i18n.t('Open User Profile Menu')}
									/>

									{#if $config?.features?.enable_user_status}
										<div class="absolute -bottom-0.5 -right-0.5">
											<span class="relative flex size-2.5">
												<span
													class="relative inline-flex size-2.5 rounded-full {true
														? 'bg-green-500'
														: 'bg-gray-300 dark:bg-gray-700'} border-2 border-white dark:border-gray-900"
												></span>
											</span>
										</div>
									{/if}
								</div>
							</div>
						</UserMenu>
					{/if}
				</div>
			</div>
		</div>
	</div>
{/if}

<!-- {$i18n.t('New Folder')} -->
<!-- {$i18n.t('Pinned')} -->

{#if $showSidebar}
	<div
		bind:this={navElement}
		id="sidebar"
		class="h-screen max-h-[100dvh] min-h-screen select-none {$showSidebar
			? `${$mobile ? 'bg-gray-50 dark:bg-gray-950' : 'bg-gray-50/70 dark:bg-gray-950/70'} z-50`
			: ' bg-transparent z-0 '} {$isApp
			? `ml-[4.5rem] md:ml-0 `
			: ' transition-all duration-300 '} shrink-0 text-gray-900 dark:text-gray-200 text-sm fixed top-0 left-0 overflow-x-hidden
        "
		transition:slide={{ duration: 250, axis: 'x' }}
		data-state={$showSidebar}
	>
		<div
			class=" my-auto flex flex-col justify-between h-screen max-h-[100dvh] w-[var(--sidebar-width)] overflow-x-hidden scrollbar-hidden z-50 {$showSidebar
				? ''
				: 'invisible'}"
		>
			<div
				class="sidebar px-[0.5625rem] pt-2 pb-1.5 flex justify-between space-x-1 text-gray-600 dark:text-gray-400 sticky top-0 z-10 -mb-3"
			>
				<a
					class="flex items-center rounded-xl size-8.5 h-full justify-center hover:bg-gray-100/50 dark:hover:bg-gray-850/50 transition no-drag-region"
					href="/"
					draggable="false"
					on:click={newChatHandler}
				>
					<div class="sidebar-new-chat-icon size-6 rounded-full overflow-hidden flex-shrink-0">
						<img src="data:image/jpeg;base64,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" alt="Garnet" class="size-6 object-cover rounded-full" />
					</div>
				</a>

				<a href="/" class="flex flex-1 px-1.5" on:click={newChatHandler}>
					<div
						id="sidebar-webui-name"
						class=" self-center font-medium text-gray-850 dark:text-white font-primary"
					>
						{$WEBUI_NAME}
					</div>
				</a>
				<Tooltip
					content={$showSidebar ? $i18n.t('Close Sidebar') : $i18n.t('Open Sidebar')}
					placement="bottom"
				>
					<button
						class="flex rounded-xl size-8.5 justify-center items-center hover:bg-gray-100/50 dark:hover:bg-gray-850/50 transition {isWindows
							? 'cursor-pointer'
							: 'cursor-[w-resize]'}"
						on:click={() => {
							showSidebar.set(!$showSidebar);
						}}
						aria-label={$showSidebar ? $i18n.t('Close Sidebar') : $i18n.t('Open Sidebar')}
					>
						<div class=" self-center p-1.5">
							<Sidebar />
						</div>
					</button>
				</Tooltip>

				<div
					class="{scrollTop > 0
						? 'visible'
						: 'invisible'} sidebar-bg-gradient-to-b bg-linear-to-b from-gray-50 dark:from-gray-950 to-transparent from-50% pointer-events-none absolute inset-0 -z-10 -mb-6"
				></div>
			</div>

			<div
				class="relative flex flex-col flex-1 overflow-y-auto scrollbar-hidden pt-3 pb-3"
				on:scroll={(e) => {
					if (e.target.scrollTop === 0) {
						scrollTop = 0;
					} else {
						scrollTop = e.target.scrollTop;
					}
				}}
			>
				<div class="pb-1.5">
					<div class="px-[0.4375rem] flex justify-center text-gray-800 dark:text-gray-200">
						<a
							id="sidebar-new-chat-button"
							class="group grow flex items-center space-x-3 rounded-2xl px-2.5 py-2 hover:bg-gray-100 dark:hover:bg-gray-900 transition outline-none"
							href="/"
							draggable="false"
							on:click={newChatHandler}
							aria-label={$i18n.t('New Chat')}
						>
							<div class="self-center">
								<PencilSquare className=" size-4.5" strokeWidth="2" />
							</div>

							<div class="flex flex-1 self-center translate-y-[0.5px]">
								<div class=" self-center text-sm font-primary">{$i18n.t('New Chat')}</div>
							</div>

							<HotkeyHint name="newChat" className=" group-hover:visible invisible" />
						</a>
					</div>

					<div class="px-[0.4375rem] flex justify-center text-gray-800 dark:text-gray-200">
						<button
							id="sidebar-search-button"
							class="group grow flex items-center space-x-3 rounded-2xl px-2.5 py-2 hover:bg-gray-100 dark:hover:bg-gray-900 transition outline-none"
							on:click={() => {
								showSearch.set(true);
							}}
							draggable="false"
							aria-label={$i18n.t('Search')}
						>
							<div class="self-center">
								<Search strokeWidth="2" className="size-4.5" />
							</div>

							<div class="flex flex-1 self-center translate-y-[0.5px]">
								<div class=" self-center text-sm font-primary">{$i18n.t('Search')}</div>
							</div>
							<HotkeyHint name="search" className=" group-hover:visible invisible" />
						</button>
					</div>

					{#if ($config?.features?.enable_notes ?? false) && ($user?.role === 'admin' || ($user?.permissions?.features?.notes ?? true))}
						<div class="px-[0.4375rem] flex justify-center text-gray-800 dark:text-gray-200">
							<a
								id="sidebar-notes-button"
								class="grow flex items-center space-x-3 rounded-2xl px-2.5 py-2 hover:bg-gray-100 dark:hover:bg-gray-900 transition"
								href="/notes"
								on:click={itemClickHandler}
								draggable="false"
								aria-label={$i18n.t('Notes')}
							>
								<div class="self-center">
									<Note className="size-4.5" strokeWidth="2" />
								</div>

								<div class="flex self-center translate-y-[0.5px]">
									<div class=" self-center text-sm font-primary">{$i18n.t('Notes')}</div>
								</div>
							</a>
						</div>
					{/if}

					{#if $user?.role === 'admin' || $user?.permissions?.workspace?.models || $user?.permissions?.workspace?.knowledge || $user?.permissions?.workspace?.prompts || $user?.permissions?.workspace?.tools}
						<div class="px-[0.4375rem] flex justify-center text-gray-800 dark:text-gray-200">
							<a
								id="sidebar-workspace-button"
								class="grow flex items-center space-x-3 rounded-2xl px-2.5 py-2 hover:bg-gray-100 dark:hover:bg-gray-900 transition"
								href="/workspace"
								on:click={itemClickHandler}
								draggable="false"
								aria-label={$i18n.t('Workspace')}
							>
								<div class="self-center">
									<svg
										xmlns="http://www.w3.org/2000/svg"
										fill="none"
										viewBox="0 0 24 24"
										stroke-width="2"
										stroke="currentColor"
										class="size-4.5"
									>
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											d="M13.5 16.875h3.375m0 0h3.375m-3.375 0V13.5m0 3.375v3.375M6 10.5h2.25a2.25 2.25 0 0 0 2.25-2.25V6a2.25 2.25 0 0 0-2.25-2.25H6A2.25 2.25 0 0 0 3.75 6v2.25A2.25 2.25 0 0 0 6 10.5Zm0 9.75h2.25A2.25 2.25 0 0 0 10.5 18v-2.25a2.25 2.25 0 0 0-2.25-2.25H6a2.25 2.25 0 0 0-2.25 2.25V18A2.25 2.25 0 0 0 6 20.25Zm9.75-9.75H18a2.25 2.25 0 0 0 2.25-2.25V6A2.25 2.25 0 0 0 18 3.75h-2.25A2.25 2.25 0 0 0 13.5 6v2.25a2.25 2.25 0 0 0 2.25 2.25Z"
										/>
									</svg>
								</div>

								<div class="flex self-center translate-y-[0.5px]">
									<div class=" self-center text-sm font-primary">{$i18n.t('Workspace')}</div>
								</div>
							</a>
						</div>
					{/if}
				</div>

				{#if ($models ?? []).length > 0 && (($settings?.pinnedModels ?? []).length > 0 || $config?.default_pinned_models)}
					<Folder
						id="sidebar-models"
						bind:open={showPinnedModels}
						className="px-2 mt-0.5"
						name={$i18n.t('Models')}
						chevron={false}
						dragAndDrop={false}
					>
						<PinnedModelList bind:selectedChatId {shiftKey} />
					</Folder>
				{/if}

				{#if $config?.features?.enable_channels && ($user?.role === 'admin' || ($user?.permissions?.features?.channels ?? true))}
					<Folder
						id="sidebar-channels"
						bind:open={showChannels}
						className="px-2 mt-0.5"
						name={$i18n.t('Channels')}
						chevron={false}
						dragAndDrop={false}
						onAdd={$user?.role === 'admin' || ($user?.permissions?.features?.channels ?? true)
							? async () => {
									await tick();

									setTimeout(() => {
										showCreateChannel = true;
									}, 0);
								}
							: null}
						onAddLabel={$i18n.t('Create Channel')}
					>
						{#each $channels as channel, channelIdx (`${channel?.id}`)}
							<ChannelItem
								{channel}
								onUpdate={async () => {
									await initChannels();
								}}
							/>

							{#if channelIdx < $channels.length - 1 && channel.type !== $channels[channelIdx + 1]?.type}<hr
									class=" border-gray-100/40 dark:border-gray-800/10 my-1.5 w-full"
								/>
							{/if}
						{/each}
					</Folder>
				{/if}

				{#if $config?.features?.enable_folders && ($user?.role === 'admin' || ($user?.permissions?.features?.folders ?? true))}
					<Folder
						id="sidebar-folders"
						bind:open={showFolders}
						className="px-2 mt-0.5"
						name={$i18n.t('Folders')}
						chevron={false}
						onAdd={() => {
							showCreateFolderModal = true;
						}}
						onAddLabel={$i18n.t('New Folder')}
						on:drop={async (e) => {
							const { type, id, item } = e.detail;

							if (type === 'folder') {
								if (folders[id].parent_id === null) {
									return;
								}

								const res = await updateFolderParentIdById(localStorage.token, id, null).catch(
									(error) => {
										toast.error(`${error}`);
										return null;
									}
								);

								if (res) {
									await initFolders();
								}
							}
						}}
					>
						<Folders
							bind:folderRegistry
							{folders}
							{shiftKey}
							onDelete={(folderId) => {
								selectedFolder.set(null);
								initChatList();
							}}
							on:update={() => {
								initChatList();
							}}
							on:import={(e) => {
								const { folderId, items } = e.detail;
								importChatHandler(items, false, folderId);
							}}
							on:change={async () => {
								initChatList();
							}}
						/>
					</Folder>
				{/if}

				<Folder
					id="sidebar-chats"
					className="px-2 mt-0.5"
					name={$i18n.t('Chats')}
					chevron={false}
					on:change={async (e) => {
						selectedFolder.set(null);
					}}
					on:import={(e) => {
						importChatHandler(e.detail);
					}}
					on:drop={async (e) => {
						const { type, id, item } = e.detail;

						if (type === 'chat') {
							let chat = await getChatById(localStorage.token, id).catch((error) => {
								return null;
							});
							if (!chat && item) {
								chat = await importChats(localStorage.token, [
									{
										chat: item.chat,
										meta: item?.meta ?? {},
										pinned: false,
										folder_id: null,
										created_at: item?.created_at ?? null,
										updated_at: item?.updated_at ?? null
									}
								]);
							}

							if (chat) {
								console.log(chat);
								if (chat.folder_id) {
									const res = await updateChatFolderIdById(localStorage.token, chat.id, null).catch(
										(error) => {
											toast.error(`${error}`);
											return null;
										}
									);

									folderRegistry[chat.folder_id]?.setFolderItems();
								}

								if (chat.pinned) {
									const res = await toggleChatPinnedStatusById(localStorage.token, chat.id);
								}

								initChatList();
							}
						} else if (type === 'folder') {
							if (folders[id].parent_id === null) {
								return;
							}

							const res = await updateFolderParentIdById(localStorage.token, id, null).catch(
								(error) => {
									toast.error(`${error}`);
									return null;
								}
							);

							if (res) {
								await initFolders();
							}
						}
					}}
				>
					{#if $pinnedChats.length > 0}
						<div class="mb-1">
							<div class="flex flex-col space-y-1 rounded-xl">
								<Folder
									id="sidebar-pinned-chats"
									buttonClassName=" text-gray-500"
									on:import={(e) => {
										importChatHandler(e.detail, true);
									}}
									on:drop={async (e) => {
										const { type, id, item } = e.detail;

										if (type === 'chat') {
											let chat = await getChatById(localStorage.token, id).catch((error) => {
												return null;
											});
											if (!chat && item) {
												chat = await importChats(localStorage.token, [
													{
														chat: item.chat,
														meta: item?.meta ?? {},
														pinned: false,
														folder_id: null,
														created_at: item?.created_at ?? null,
														updated_at: item?.updated_at ?? null
													}
												]);
											}

											if (chat) {
												console.log(chat);
												if (chat.folder_id) {
													const res = await updateChatFolderIdById(
														localStorage.token,
														chat.id,
														null
													).catch((error) => {
														toast.error(`${error}`);
														return null;
													});
												}

												if (!chat.pinned) {
													const res = await toggleChatPinnedStatusById(localStorage.token, chat.id);
												}

												initChatList();
											}
										}
									}}
									name={$i18n.t('Pinned')}
								>
									<div
										class="ml-3 pl-1 mt-[1px] flex flex-col overflow-y-auto scrollbar-hidden border-s border-gray-100 dark:border-gray-900 text-gray-900 dark:text-gray-200"
									>
										{#each $pinnedChats as chat, idx (`pinned-chat-${chat?.id ?? idx}`)}
											<ChatItem
												className=""
												id={chat.id}
												title={chat.title}
												createdAt={chat.created_at}
												{shiftKey}
												selected={selectedChatId === chat.id}
												on:select={() => {
													selectedChatId = chat.id;
												}}
												on:unselect={() => {
													selectedChatId = null;
												}}
												on:change={async () => {
													initChatList();
												}}
												on:tag={(e) => {
													const { type, name } = e.detail;
													tagEventHandler(type, name, chat.id);
												}}
											/>
										{/each}
									</div>
								</Folder>
							</div>
						</div>
					{/if}

					<div class=" flex-1 flex flex-col overflow-y-auto scrollbar-hidden">
						<div class="pt-1.5">
							{#if $chats}
								{#each $chats as chat, idx (`chat-${chat?.id ?? idx}`)}
									{#if idx === 0 || (idx > 0 && chat.time_range !== $chats[idx - 1].time_range)}
										<div
											class="w-full pl-2.5 text-xs text-gray-500 dark:text-gray-500 font-medium {idx ===
											0
												? ''
												: 'pt-5'} pb-1.5"
										>
											{$i18n.t(chat.time_range)}
											<!-- localisation keys for time_range to be recognized from the i18next parser (so they don't get automatically removed):
							{$i18n.t('Today')}
							{$i18n.t('Yesterday')}
							{$i18n.t('Previous 7 days')}
							{$i18n.t('Previous 30 days')}
							{$i18n.t('January')}
							{$i18n.t('February')}
							{$i18n.t('March')}
							{$i18n.t('April')}
							{$i18n.t('May')}
							{$i18n.t('June')}
							{$i18n.t('July')}
							{$i18n.t('August')}
							{$i18n.t('September')}
							{$i18n.t('October')}
							{$i18n.t('November')}
							{$i18n.t('December')}
							-->
										</div>
									{/if}

									<ChatItem
										className=""
										id={chat.id}
										title={chat.title}
										createdAt={chat.created_at}
										{shiftKey}
										selected={selectedChatId === chat.id}
										on:select={() => {
											selectedChatId = chat.id;
										}}
										on:unselect={() => {
											selectedChatId = null;
										}}
										on:change={async () => {
											initChatList();
										}}
										on:tag={(e) => {
											const { type, name } = e.detail;
											tagEventHandler(type, name, chat.id);
										}}
									/>
								{/each}

								{#if $scrollPaginationEnabled && !allChatsLoaded}
									<Loader
										on:visible={(e) => {
											if (!chatListLoading) {
												loadMoreChats();
											}
										}}
									>
										<div
											class="w-full flex justify-center py-1 text-xs animate-pulse items-center gap-2"
										>
											<Spinner className=" size-4" />
											<div class=" ">{$i18n.t('Loading...')}</div>
										</div>
									</Loader>
								{/if}
							{:else}
								<div
									class="w-full flex justify-center py-1 text-xs animate-pulse items-center gap-2"
								>
									<Spinner className=" size-4" />
									<div class=" ">{$i18n.t('Loading...')}</div>
								</div>
							{/if}
						</div>
					</div>
				</Folder>
			</div>

			<div class="px-1.5 pt-1.5 pb-2 sticky bottom-0 z-10 -mt-3 sidebar">
				<div
					class=" sidebar-bg-gradient-to-t bg-linear-to-t from-gray-50 dark:from-gray-950 to-transparent from-50% pointer-events-none absolute inset-0 -z-10 -mt-6"
				></div>
				<div class="flex flex-col font-primary">
					{#if $user !== undefined && $user !== null}
						<UserMenu
							role={$user?.role}
							profile={$config?.features?.enable_user_status ?? true}
							showActiveUsers={false}
							className="w-[calc(var(--sidebar-width)-1rem)]"
							on:show={(e) => {
								if (e.detail === 'archived-chat') {
									showArchivedChats.set(true);
								}
							}}
						>
							<div
								class=" flex items-center rounded-2xl py-2 px-1.5 w-full hover:bg-gray-100/50 dark:hover:bg-gray-900/50 transition"
							>
								<div class=" self-center mr-3 relative">
									<img
										src={`${WEBUI_API_BASE_URL}/users/${$user?.id}/profile/image`}
										class=" size-7 object-cover rounded-full"
										alt={$i18n.t('Open User Profile Menu')}
										aria-label={$i18n.t('Open User Profile Menu')}
									/>

									{#if $config?.features?.enable_user_status}
										<div class="absolute -bottom-0.5 -right-0.5">
											<span class="relative flex size-2.5">
												<span
													class="relative inline-flex size-2.5 rounded-full {true
														? 'bg-green-500'
														: 'bg-gray-300 dark:bg-gray-700'} border-2 border-white dark:border-gray-900"
												></span>
											</span>
										</div>
									{/if}
								</div>
								<div class=" self-center font-medium">{$user?.name}</div>
							</div>
						</UserMenu>
					{/if}
				</div>
			</div>
		</div>
	</div>

	{#if !$mobile}
		<div
			class="relative flex items-center justify-center group border-l border-gray-50 dark:border-gray-850/30 hover:border-gray-200 dark:hover:border-gray-800 transition z-20"
			id="sidebar-resizer"
			on:mousedown={resizeStartHandler}
			role="separator"
		>
			<div
				class=" absolute -left-1.5 -right-1.5 -top-0 -bottom-0 z-20 cursor-col-resize bg-transparent"
			/>
		</div>
	{/if}
{/if}
