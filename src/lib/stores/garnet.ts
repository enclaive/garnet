import { writable } from 'svelte/store';

const STORAGE_KEY = 'garnet_query_expand';

function loadInitial(): boolean {
	if (typeof window === 'undefined') return false;
	try {
		return localStorage.getItem(STORAGE_KEY) === 'true';
	} catch {
		return false;
	}
}

export const queryExpand = writable<boolean>(loadInitial());

if (typeof window !== 'undefined') {
	queryExpand.subscribe((val) => {
		try {
			localStorage.setItem(STORAGE_KEY, val ? 'true' : 'false');
		} catch {}
	});
}
