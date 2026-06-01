<script lang="ts">
	import DOMPurify from 'dompurify';
	import { marked } from 'marked';

	import { toast } from 'svelte-sonner';

	import { onMount, getContext, tick } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';

	import { getBackendConfig } from '$lib/apis';
	import {
		ldapUserSignIn,
		getSessionUser,
		userSignIn,
		userSignUp,
		updateUserTimezone
	} from '$lib/apis/auths';

	import { WEBUI_API_BASE_URL, WEBUI_BASE_URL } from '$lib/constants';
	import { WEBUI_NAME, config, user, socket } from '$lib/stores';

	import { generateInitialsImage, canvasPixelTest, getUserTimezone } from '$lib/utils';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import OnBoarding from '$lib/components/OnBoarding.svelte';
	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';
	import { redirect } from '@sveltejs/kit';

	const i18n = getContext('i18n');

	let loaded = false;

	let mode = $config?.features.enable_ldap ? 'ldap' : 'signin';

	let form = null;

	let name = '';
	let email = '';
	let password = '';
	let confirmPassword = '';

	let ldapUsername = '';

	const setSessionUser = async (sessionUser, redirectPath: string | null = null) => {
		if (sessionUser) {
			console.log(sessionUser);
			toast.success($i18n.t(`You're now logged in.`));
			if (sessionUser.token) {
				localStorage.token = sessionUser.token;
			}
			$socket.emit('user-join', { auth: { token: sessionUser.token } });
			await user.set(sessionUser);
			await config.set(await getBackendConfig());

			// Update user timezone
			const timezone = getUserTimezone();
			if (sessionUser.token && timezone) {
				updateUserTimezone(sessionUser.token, timezone);
			}

			if (!redirectPath) {
				redirectPath = $page.url.searchParams.get('redirect') || '/';
			}

			goto(redirectPath);
			localStorage.removeItem('redirectPath');
		}
	};

	const signInHandler = async () => {
		const sessionUser = await userSignIn(email, password).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		await setSessionUser(sessionUser);
	};

	const signUpHandler = async () => {
		if ($config?.features?.enable_signup_password_confirmation) {
			if (password !== confirmPassword) {
				toast.error($i18n.t('Passwords do not match.'));
				return;
			}
		}

		const sessionUser = await userSignUp(name, email, password, generateInitialsImage(name)).catch(
			(error) => {
				toast.error(`${error}`);
				return null;
			}
		);

		await setSessionUser(sessionUser);
	};

	const ldapSignInHandler = async () => {
		const sessionUser = await ldapUserSignIn(ldapUsername, password).catch((error) => {
			toast.error(`${error}`);
			return null;
		});
		await setSessionUser(sessionUser);
	};

	const submitHandler = async () => {
		if (mode === 'ldap') {
			await ldapSignInHandler();
		} else if (mode === 'signin') {
			await signInHandler();
		} else {
			await signUpHandler();
		}
	};

	const oauthCallbackHandler = async () => {
		// Get the value of the 'token' cookie
		function getCookie(name) {
			const match = document.cookie.match(
				new RegExp('(?:^|; )' + name.replace(/([.$?*|{}()[\]\\/+^])/g, '\\$1') + '=([^;]*)')
			);
			return match ? decodeURIComponent(match[1]) : null;
		}

		const token = getCookie('token');
		if (!token) {
			return;
		}

		const sessionUser = await getSessionUser(token).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (!sessionUser) {
			return;
		}

		localStorage.token = token;
		await setSessionUser(sessionUser, localStorage.getItem('redirectPath') || null);
	};

	let onboarding = false;

	async function setLogoImage() {
		await tick();
		const logo = document.getElementById('logo');

		if (logo) {
			const isDarkMode = document.documentElement.classList.contains('dark');

			if (isDarkMode) {
				const darkImage = new Image();
				darkImage.src = `${WEBUI_BASE_URL}/static/favicon-dark.png`;

				darkImage.onload = () => {
					logo.src = `${WEBUI_BASE_URL}/static/favicon-dark.png`;
					logo.style.filter = ''; // Ensure no inversion is applied if favicon-dark.png exists
				};

				darkImage.onerror = () => {
					logo.style.filter = 'invert(1)'; // Invert image if favicon-dark.png is missing
				};
			}
		}
	}

	onMount(async () => {
		const redirectPath = $page.url.searchParams.get('redirect');
		if ($user !== undefined) {
			goto(redirectPath || '/');
		} else {
			if (redirectPath) {
				localStorage.setItem('redirectPath', redirectPath);
			}
		}

		const error = $page.url.searchParams.get('error');
		if (error) {
			toast.error(error);
		}

		await oauthCallbackHandler();
		form = $page.url.searchParams.get('form');

		loaded = true;
		setLogoImage();

		if (($config?.features.auth_trusted_header ?? false) || $config?.features.auth === false) {
			await signInHandler();
		} else {
			onboarding = $config?.onboarding ?? false;
		}
	});
</script>

<svelte:head>
	<title>
		{`${$WEBUI_NAME}`}
	</title>
</svelte:head>

<OnBoarding
	bind:show={onboarding}
	getStartedHandler={() => {
		onboarding = false;
		mode = $config?.features.enable_ldap ? 'ldap' : 'signup';
	}}
/>

<div class="w-full h-screen max-h-[100dvh] text-white relative" id="auth-page">
	<div class="w-full h-full absolute top-0 left-0 bg-white dark:bg-black"></div>

	<div class="w-full absolute top-0 left-0 right-0 h-8 drag-region" />

	{#if loaded}
		<div
			class="fixed bg-transparent min-h-screen w-full flex justify-center font-primary z-50 text-black dark:text-white"
			id="auth-container"
		>
			<div class="w-full px-10 min-h-screen flex flex-col text-center">
				{#if ($config?.features.auth_trusted_header ?? false) || $config?.features.auth === false}
					<div class=" my-auto pb-10 w-full sm:max-w-md">
						<div
							class="flex items-center justify-center gap-3 text-xl sm:text-2xl text-center font-medium dark:text-gray-200"
						>
							<div>
								{$i18n.t('Signing in to {{WEBUI_NAME}}', { WEBUI_NAME: $WEBUI_NAME })}
							</div>

							<div>
								<Spinner className="size-5" />
							</div>
						</div>
					</div>
				{:else}
					<div class="my-auto flex flex-col justify-center items-center">
						<div class=" sm:max-w-md my-auto pb-10 w-full dark:text-gray-100">
									<div class="flex justify-center mb-6">
									<div class="size-24 rounded-full overflow-hidden flex items-center justify-center bg-white dark:bg-gray-800">
									<img src="data:image/jpeg;base64,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" alt="Garnet" class="size-24 object-cover rounded-full" />
								</div>
								</div>
							<form
								class=" flex flex-col justify-center"
								on:submit={(e) => {
									e.preventDefault();
									submitHandler();
								}}
							>
								<div class="mb-1">
									<div class=" text-2xl font-medium">
										{#if $config?.onboarding ?? false}
											{$i18n.t(`Get started with {{WEBUI_NAME}}`, { WEBUI_NAME: $WEBUI_NAME })}
										{:else if mode === 'ldap'}
											{$i18n.t(`Sign in to {{WEBUI_NAME}} with LDAP`, { WEBUI_NAME: $WEBUI_NAME })}
										{:else if mode === 'signin'}
											{$i18n.t(`Sign in to {{WEBUI_NAME}}`, { WEBUI_NAME: $WEBUI_NAME })}
										{:else}
											{$i18n.t(`Sign up to {{WEBUI_NAME}}`, { WEBUI_NAME: $WEBUI_NAME })}
										{/if}
									</div>

									{#if $config?.onboarding ?? false}
										<div class="mt-1 text-xs font-medium text-gray-600 dark:text-gray-500">
											ⓘ {$WEBUI_NAME}
											{$i18n.t(
												'does not make any external connections, and your data stays securely on your locally hosted server.'
											)}
										</div>
									{/if}
								</div>

								{#if $config?.features.enable_login_form || $config?.features.enable_ldap || form}
									<div class="flex flex-col mt-4">
										{#if mode === 'signup'}
											<div class="mb-2">
												<label for="name" class="text-sm font-medium text-left mb-1 block"
													>{$i18n.t('Name')}</label
												>
												<input
													bind:value={name}
													type="text"
													id="name"
													class="my-0.5 w-full text-sm outline-hidden bg-transparent placeholder:text-gray-300 dark:placeholder:text-gray-600"
													autocomplete="name"
													placeholder={$i18n.t('Enter Your Full Name')}
													required
												/>
											</div>
										{/if}

										{#if mode === 'ldap'}
											<div class="mb-2">
												<label for="username" class="text-sm font-medium text-left mb-1 block"
													>{$i18n.t('Username')}</label
												>
												<input
													bind:value={ldapUsername}
													type="text"
													class="my-0.5 w-full text-sm outline-hidden bg-transparent placeholder:text-gray-300 dark:placeholder:text-gray-600"
													autocomplete="username"
													name="username"
													id="username"
													placeholder={$i18n.t('Enter Your Username')}
													required
												/>
											</div>
										{:else}
											<div class="mb-2">
												<label for="email" class="text-sm font-medium text-left mb-1 block"
													>{$i18n.t('Email')}</label
												>
												<input
													bind:value={email}
													type="email"
													id="email"
													class="my-0.5 w-full text-sm outline-hidden bg-transparent placeholder:text-gray-300 dark:placeholder:text-gray-600"
													autocomplete="email"
													name="email"
													placeholder={$i18n.t('Enter Your Email')}
													required
												/>
											</div>
										{/if}

										<div>
											<label for="password" class="text-sm font-medium text-left mb-1 block"
												>{$i18n.t('Password')}</label
											>
											<SensitiveInput
												bind:value={password}
												type="password"
												id="password"
												class="my-0.5 w-full text-sm outline-hidden bg-transparent placeholder:text-gray-300 dark:placeholder:text-gray-600"
												placeholder={$i18n.t('Enter Your Password')}
												autocomplete={mode === 'signup' ? 'new-password' : 'current-password'}
												name="password"
												screenReader={true}
												required
												aria-required="true"
											/>
										</div>

										{#if mode === 'signup' && $config?.features?.enable_signup_password_confirmation}
											<div class="mt-2">
												<label
													for="confirm-password"
													class="text-sm font-medium text-left mb-1 block"
													>{$i18n.t('Confirm Password')}</label
												>
												<SensitiveInput
													bind:value={confirmPassword}
													type="password"
													id="confirm-password"
													class="my-0.5 w-full text-sm outline-hidden bg-transparent"
													placeholder={$i18n.t('Confirm Your Password')}
													autocomplete="new-password"
													name="confirm-password"
													required
												/>
											</div>
										{/if}
									</div>
								{/if}
								<div class="mt-5">
									{#if $config?.features.enable_login_form || $config?.features.enable_ldap || form}
										{#if mode === 'ldap'}
											<button
												class="bg-gray-700/5 hover:bg-gray-700/10 dark:bg-gray-100/5 dark:hover:bg-gray-100/10 dark:text-gray-300 dark:hover:text-white transition w-full rounded-full font-medium text-sm py-2.5"
												type="submit"
											>
												{$i18n.t('Authenticate')}
											</button>
										{:else}
											<button
												class="bg-gray-700/5 hover:bg-gray-700/10 dark:bg-gray-100/5 dark:hover:bg-gray-100/10 dark:text-gray-300 dark:hover:text-white transition w-full rounded-full font-medium text-sm py-2.5"
												type="submit"
											>
												{mode === 'signin'
													? $i18n.t('Sign in')
													: ($config?.onboarding ?? false)
														? $i18n.t('Create Admin Account')
														: $i18n.t('Create Account')}
											</button>

											{#if $config?.features.enable_signup && !($config?.onboarding ?? false)}
												<div class=" mt-4 text-sm text-center">
													{mode === 'signin'
														? $i18n.t("Don't have an account?")
														: $i18n.t('Already have an account?')}

													<button
														class=" font-medium underline"
														type="button"
														on:click={() => {
															if (mode === 'signin') {
																mode = 'signup';
															} else {
																mode = 'signin';
															}
														}}
													>
														{mode === 'signin' ? $i18n.t('Sign up') : $i18n.t('Sign in')}
													</button>
												</div>
											{/if}
										{/if}
									{/if}
								</div>
							</form>

							{#if Object.keys($config?.oauth?.providers ?? {}).length > 0}
								<div class="inline-flex items-center justify-center w-full">
									<hr class="w-32 h-px my-4 border-0 dark:bg-gray-100/10 bg-gray-700/10" />
									{#if $config?.features.enable_login_form || $config?.features.enable_ldap || form}
										<span
											class="px-3 text-sm font-medium text-gray-900 dark:text-white bg-transparent"
											>{$i18n.t('or')}</span
										>
									{/if}

									<hr class="w-32 h-px my-4 border-0 dark:bg-gray-100/10 bg-gray-700/10" />
								</div>
								<div class="flex flex-col space-y-2">
									{#if $config?.oauth?.providers?.google}
										<button
											class="flex justify-center items-center bg-gray-700/5 hover:bg-gray-700/10 dark:bg-gray-100/5 dark:hover:bg-gray-100/10 dark:text-gray-300 dark:hover:text-white transition w-full rounded-full font-medium text-sm py-2.5"
											on:click={() => {
												window.location.href = `${WEBUI_BASE_URL}/oauth/google/login`;
											}}
										>
											<svg
												xmlns="http://www.w3.org/2000/svg"
												viewBox="0 0 48 48"
												class="size-6 mr-3"
												aria-hidden="true"
											>
												<path
													fill="#EA4335"
													d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"
												/><path
													fill="#4285F4"
													d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"
												/><path
													fill="#FBBC05"
													d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"
												/><path
													fill="#34A853"
													d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"
												/><path fill="none" d="M0 0h48v48H0z" />
											</svg>
											<span>{$i18n.t('Continue with {{provider}}', { provider: 'Google' })}</span>
										</button>
									{/if}
									{#if $config?.oauth?.providers?.microsoft}
										<button
											class="flex justify-center items-center bg-gray-700/5 hover:bg-gray-700/10 dark:bg-gray-100/5 dark:hover:bg-gray-100/10 dark:text-gray-300 dark:hover:text-white transition w-full rounded-full font-medium text-sm py-2.5"
											on:click={() => {
												window.location.href = `${WEBUI_BASE_URL}/oauth/microsoft/login`;
											}}
										>
											<svg
												xmlns="http://www.w3.org/2000/svg"
												viewBox="0 0 21 21"
												class="size-6 mr-3"
												aria-hidden="true"
											>
												<rect x="1" y="1" width="9" height="9" fill="#f25022" /><rect
													x="1"
													y="11"
													width="9"
													height="9"
													fill="#00a4ef"
												/><rect x="11" y="1" width="9" height="9" fill="#7fba00" /><rect
													x="11"
													y="11"
													width="9"
													height="9"
													fill="#ffb900"
												/>
											</svg>
											<span>{$i18n.t('Continue with {{provider}}', { provider: 'Microsoft' })}</span
											>
										</button>
									{/if}
									{#if $config?.oauth?.providers?.github}
										<button
											class="flex justify-center items-center bg-gray-700/5 hover:bg-gray-700/10 dark:bg-gray-100/5 dark:hover:bg-gray-100/10 dark:text-gray-300 dark:hover:text-white transition w-full rounded-full font-medium text-sm py-2.5"
											on:click={() => {
												window.location.href = `${WEBUI_BASE_URL}/oauth/github/login`;
											}}
										>
											<svg
												xmlns="http://www.w3.org/2000/svg"
												viewBox="0 0 24 24"
												class="size-6 mr-3"
												aria-hidden="true"
											>
												<path
													fill="currentColor"
													d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.92 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57C20.565 21.795 24 17.31 24 12c0-6.63-5.37-12-12-12z"
												/>
											</svg>
											<span>{$i18n.t('Continue with {{provider}}', { provider: 'GitHub' })}</span>
										</button>
									{/if}
									{#if $config?.oauth?.providers?.oidc}
										<button
											class="flex justify-center items-center bg-gray-700/5 hover:bg-gray-700/10 dark:bg-gray-100/5 dark:hover:bg-gray-100/10 dark:text-gray-300 dark:hover:text-white transition w-full rounded-full font-medium text-sm py-2.5"
											on:click={() => {
												window.location.href = `${WEBUI_BASE_URL}/oauth/oidc/login`;
											}}
										>
											<svg
												xmlns="http://www.w3.org/2000/svg"
												fill="none"
												viewBox="0 0 24 24"
												stroke-width="1.5"
												stroke="currentColor"
												class="size-6 mr-3"
												aria-hidden="true"
											>
												<path
													stroke-linecap="round"
													stroke-linejoin="round"
													d="M15.75 5.25a3 3 0 0 1 3 3m3 0a6 6 0 0 1-7.029 5.912c-.563-.097-1.159.026-1.563.43L10.5 17.25H8.25v2.25H6v2.25H2.25v-2.818c0-.597.237-1.17.659-1.591l6.499-6.499c.404-.404.527-1 .43-1.563A6 6 0 1 1 21.75 8.25Z"
												/>
											</svg>

											<span
												>{$i18n.t('Continue with {{provider}}', {
													provider: $config?.oauth?.providers?.oidc ?? 'SSO'
												})}</span
											>
										</button>
									{/if}
									{#if $config?.oauth?.providers?.feishu}
										<button
											class="flex justify-center items-center bg-gray-700/5 hover:bg-gray-700/10 dark:bg-gray-100/5 dark:hover:bg-gray-100/10 dark:text-gray-300 dark:hover:text-white transition w-full rounded-full font-medium text-sm py-2.5"
											on:click={() => {
												window.location.href = `${WEBUI_BASE_URL}/oauth/feishu/login`;
											}}
										>
											<span>{$i18n.t('Continue with {{provider}}', { provider: 'Feishu' })}</span>
										</button>
									{/if}
								</div>
							{/if}

							{#if $config?.features.enable_ldap && $config?.features.enable_login_form}
								<div class="mt-2">
									<button
										class="flex justify-center items-center text-xs w-full text-center underline"
										type="button"
										on:click={() => {
											if (mode === 'ldap')
												mode = ($config?.onboarding ?? false) ? 'signup' : 'signin';
											else mode = 'ldap';
										}}
									>
										<span
											>{mode === 'ldap'
												? $i18n.t('Continue with Email')
												: $i18n.t('Continue with LDAP')}</span
										>
									</button>
								</div>
							{/if}
						</div>
						{#if $config?.metadata?.login_footer}
							<div class="max-w-3xl mx-auto">
								<div class="mt-2 text-[0.7rem] text-gray-500 dark:text-gray-400 marked">
									{@html DOMPurify.sanitize(marked($config?.metadata?.login_footer))}
								</div>
							</div>
					</div>
				{/if}
			</div>
		</div>

		{#if !$config?.metadata?.auth_logo_position}
			<div class="fixed m-10 z-50">
				<div class="flex space-x-2">
					<div class=" self-center">
						<div class="size-6 rounded-full overflow-hidden flex-shrink-0">
							<img src="data:image/jpeg;base64,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" alt="Garnet" class="size-6 object-cover rounded-full" />
						</div>
					</div>
				</div>
			</div>
		{/if}
	{/if}
</div>
