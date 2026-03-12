import math
import random

import requests
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import Http404, JsonResponse
from django.shortcuts import redirect, render

POKEAPI_BASE_URL = 'https://pokeapi.co/api/v2/pokemon'
POKEAPI_TYPE_URL = 'https://pokeapi.co/api/v2/type'
PAGE_SIZE = 20


def get_pokemon_image(pokemon_id):
    return f'https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/{pokemon_id}.png'


def extract_pokemon_id(url):
    return url.rstrip('/').split('/')[-1]


def build_pokemon_summary(index, name, url):
    pokemon_id = extract_pokemon_id(url)
    return {
        'index': index,
        'id': pokemon_id,
        'name': name,
        'url': url,
        'image': get_pokemon_image(pokemon_id),
    }


def fetch_pokemon_detail(name):
    response = requests.get(f'{POKEAPI_BASE_URL}/{name.lower()}', timeout=10)
    response.raise_for_status()
    payload = response.json()

    types = [entry['type']['name'] for entry in payload.get('types', [])]
    abilities = [entry['ability']['name'] for entry in payload.get('abilities', [])]
    stats = {entry['stat']['name']: entry['base_stat'] for entry in payload.get('stats', [])}

    return {
        'id': payload['id'],
        'name': payload['name'],
        'url': f'{POKEAPI_BASE_URL}/{payload["id"]}/',
        'height': payload['height'],
        'weight': payload['weight'],
        'types': types,
        'abilities': abilities,
        'stats': stats,
        'image': payload.get('sprites', {}).get('front_default') or get_pokemon_image(payload['id']),
    }


def fetch_pokemon_types():
    response = requests.get(f'{POKEAPI_TYPE_URL}/', timeout=10)
    response.raise_for_status()
    payload = response.json()
    return sorted(
        [entry['name'] for entry in payload.get('results', []) if entry['name'] not in {'unknown', 'shadow'}]
    )


def fetch_all_pokemon_names():
    response = requests.get(
        POKEAPI_BASE_URL,
        params={'limit': 2000, 'offset': 0},
        timeout=10,
    )
    response.raise_for_status()
    payload = response.json()
    return [entry['name'] for entry in payload.get('results', [])]


def fetch_pokemon_list(page, name_filter='', type_filter=''):
    safe_page = max(page, 1)
    normalized_name = name_filter.strip().lower()
    normalized_type = type_filter.strip().lower()

    if normalized_name:
        try:
            pokemon = fetch_pokemon_detail(normalized_name)
        except requests.HTTPError as exc:
            if exc.response is not None and exc.response.status_code == 404:
                return {
                    'count': 0,
                    'results': [],
                    'page': 1,
                    'page_size': PAGE_SIZE,
                    'total_pages': 1,
                    'loaded_count': 0,
                    'has_more': False,
                }
            raise
        if normalized_type and normalized_type not in pokemon['types']:
            results = []
        else:
            results = [build_pokemon_summary(1, pokemon['name'], pokemon['url'])]
        return {
            'count': len(results),
            'results': results,
            'page': 1,
            'page_size': PAGE_SIZE,
            'total_pages': 1,
            'loaded_count': len(results),
            'has_more': False,
        }

    if normalized_type:
        response = requests.get(f'{POKEAPI_TYPE_URL}/{normalized_type}/', timeout=10)
        response.raise_for_status()
        payload = response.json()
        all_pokemon = payload.get('pokemon', [])
        loaded_count = min(len(all_pokemon), safe_page * PAGE_SIZE)
        results = []
        for index, entry in enumerate(all_pokemon[:loaded_count], start=1):
            pokemon_resource = entry['pokemon']
            results.append(build_pokemon_summary(index, pokemon_resource['name'], pokemon_resource['url']))

        total_pages = math.ceil(len(all_pokemon) / PAGE_SIZE) if all_pokemon else 1
        return {
            'count': len(all_pokemon),
            'results': results,
            'page': safe_page,
            'page_size': PAGE_SIZE,
            'total_pages': total_pages,
            'loaded_count': len(results),
            'has_more': len(results) < len(all_pokemon),
        }

    response = requests.get(
        POKEAPI_BASE_URL,
        params={'limit': safe_page * PAGE_SIZE, 'offset': 0},
        timeout=10,
    )
    response.raise_for_status()
    payload = response.json()
    total_pages = math.ceil(payload['count'] / PAGE_SIZE) if payload['count'] else 1

    results = []
    for index, pokemon in enumerate(payload.get('results', []), start=1):
        results.append(build_pokemon_summary(index, pokemon['name'], pokemon['url']))

    return {
        'count': payload['count'],
        'results': results,
        'page': safe_page,
        'page_size': PAGE_SIZE,
        'total_pages': total_pages,
        'loaded_count': len(results),
        'has_more': len(results) < payload['count'],
    }


@login_required
def home_view(request):
    try:
        page = int(request.GET.get('page', 1) or 1)
    except ValueError:
        page = 1

    name_filter = request.GET.get('name', '').strip()
    type_filter = request.GET.get('type', '').strip()
    error = None
    pokemon_page = {
        'count': 0,
        'results': [],
        'page': page,
        'total_pages': 1,
        'loaded_count': 0,
        'has_more': False,
    }
    pokemon_types = []

    try:
        pokemon_types = fetch_pokemon_types()
        pokemon_page = fetch_pokemon_list(page, name_filter=name_filter, type_filter=type_filter)
    except requests.RequestException:
        error = 'No se pudo cargar la lista de Pokemon.'

    context = {
        'error': error,
        'pokemon_page': pokemon_page,
        'pokemon_types': pokemon_types,
        'name_filter': name_filter,
        'type_filter': type_filter,
        'next_page': pokemon_page['page'] + 1,
    }
    return render(request, 'users/home.html', context)


def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('home')
        return render(request, 'users/login.html', {
            'error': 'Usuario o contrasena incorrectos.',
            'username': username,
        })

    return render(request, 'users/login.html')


def logout_view(request):
    logout(request)
    return redirect('login')


def build_battle_pokemon(name):
    pokemon = fetch_pokemon_detail(name)
    return {
        'id': pokemon['id'],
        'name': pokemon['name'],
        'image': pokemon['image'],
        'types': pokemon['types'],
        'stats': {
            'hp': pokemon['stats'].get('hp', 1),
            'attack': pokemon['stats'].get('attack', 1),
            'defense': pokemon['stats'].get('defense', 1),
            'special_attack': pokemon['stats'].get('special-attack', 1),
            'special_defense': pokemon['stats'].get('special-defense', 1),
            'speed': pokemon['stats'].get('speed', 1),
        },
        'current_hp_percent': 100,
        'turns_taken': 0,
        'shield': 1.0,
    }


def build_battle_card(pokemon):
    return {
        'id': pokemon['id'],
        'name': pokemon['name'],
        'image': pokemon['image'],
        'types': pokemon['types'],
        'stats': pokemon['stats'],
        'current_hp_percent': 100,
    }


def choose_battle_action(pokemon):
    actions = ['attack', 'defend']
    if pokemon['turns_taken'] >= 3:
        actions.append('special_defend')
    if pokemon['turns_taken'] >= 4:
        actions.append('special_attack')
    return random.choice(actions)


def simulate_battle(first_name, second_name):
    left = build_battle_pokemon(first_name)
    right = build_battle_pokemon(second_name)
    left_card = build_battle_card(left)
    right_card = build_battle_card(right)

    fighters = sorted(
        [left, right],
        key=lambda pokemon: (pokemon['stats']['speed'], pokemon['stats']['attack']),
        reverse=True,
    )

    steps = []
    round_number = 1
    turn_number = 1

    while left['current_hp_percent'] > 0 and right['current_hp_percent'] > 0 and turn_number <= 50:
        attacker = fighters[(turn_number - 1) % 2]
        defender = fighters[turn_number % 2]
        attacker['turns_taken'] += 1
        action = choose_battle_action(attacker)
        failed = random.random() < 0.2
        damage = 0
        action_label = {
            'attack': 'Ataque',
            'special_attack': 'Ataque especial',
            'defend': 'Defensa',
            'special_defend': 'Defensa especial',
        }[action]

        if action in {'defend', 'special_defend'}:
            if failed:
                log = (
                    f'Turno {turn_number}: {attacker["name"]} intento {action_label.lower()} '
                    f'pero fallo. {defender["name"]} sigue con {defender["current_hp_percent"]}% de vida.'
                )
            else:
                attacker['shield'] = 0.6 if action == 'defend' else 0.35
                log = (
                    f'Turno {turn_number}: {attacker["name"]} uso {action_label.lower()}. '
                    f'Se preparo para reducir el siguiente dano.'
                )
        else:
            if failed:
                log = (
                    f'Turno {turn_number}: {attacker["name"]} uso {action_label.lower()} '
                    f'pero fallo. {defender["name"]} queda con {defender["current_hp_percent"]}% de vida.'
                )
            else:
                attack_stat = attacker['stats']['attack']
                defense_stat = defender['stats']['defense']
                variance = random.randint(8, 16)

                if action == 'special_attack':
                    attack_stat = attacker['stats']['special_attack']
                    defense_stat = defender['stats']['special_defense']
                    variance = random.randint(14, 24)

                raw_damage = max(6, round((attack_stat - defense_stat * 0.35 + variance) / 3))
                damage = max(4, min(35, raw_damage))
                if defender['shield'] < 1.0:
                    damage = max(1, round(damage * defender['shield']))
                defender['shield'] = 1.0
                defender['current_hp_percent'] = max(0, defender['current_hp_percent'] - damage)
                log = (
                    f'Turno {turn_number}: {attacker["name"]} uso {action_label.lower()} e hizo '
                    f'{damage}% de dano. {defender["name"]} queda con {defender["current_hp_percent"]}% de vida.'
                )

        steps.append({
            'turn': turn_number,
            'message': log,
            'left_hp': left['current_hp_percent'],
            'right_hp': right['current_hp_percent'],
        })
        if turn_number % 2 == 0:
            round_number += 1
        if defender['current_hp_percent'] <= 0:
            break
        turn_number += 1

    winner = left if left['current_hp_percent'] >= right['current_hp_percent'] else right
    loser = right if winner is left else left

    return {
        'left': left_card,
        'right': right_card,
        'winner': winner,
        'loser': loser,
        'steps': steps,
        'rounds': round_number,
    }


@login_required
def battle_view(request):
    battle = None
    error = None
    pokemon_names = []
    first_choice = request.POST.get('first_pokemon', '').strip()
    second_choice = request.POST.get('second_pokemon', '').strip()

    try:
        pokemon_names = fetch_all_pokemon_names()
        if request.method == 'POST':
            if not first_choice or not second_choice:
                error = 'Debes elegir dos Pokemon.'
            elif first_choice.lower() == second_choice.lower():
                error = 'Debes elegir dos Pokemon distintos.'
            else:
                battle = simulate_battle(first_choice, second_choice)
    except requests.HTTPError as exc:
        if exc.response is not None and exc.response.status_code == 404:
            error = 'Uno de los Pokemon no existe.'
        else:
            error = 'No se pudo cargar la pelea.'
    except requests.RequestException:
        error = 'No se pudo cargar la pelea.'

    return render(request, 'users/battle.html', {
        'battle': battle,
        'error': error,
        'pokemon_names': pokemon_names,
        'first_choice': first_choice,
        'second_choice': second_choice,
    })


@login_required
def pokemon_detail_view(request, name):
    try:
        pokemon = fetch_pokemon_detail(name)
    except requests.HTTPError as exc:
        if exc.response is not None and exc.response.status_code == 404:
            raise Http404('Pokemon no encontrado.')
        pokemon = None
    except requests.RequestException:
        pokemon = None

    return render(request, 'users/detail.html', {'pokemon': pokemon, 'name': name})


@login_required
def pokemon_list_api(request):
    try:
        page = int(request.GET.get('page', 1) or 1)
        name_filter = request.GET.get('name', '').strip()
        type_filter = request.GET.get('type', '').strip()
        return JsonResponse(fetch_pokemon_list(page, name_filter=name_filter, type_filter=type_filter))
    except (ValueError, requests.RequestException):
        return JsonResponse({'error': 'No se pudo obtener la lista de Pokemon.'}, status=502)


@login_required
def pokemon_detail_api(request, name):
    try:
        return JsonResponse(fetch_pokemon_detail(name))
    except requests.HTTPError as exc:
        status_code = exc.response.status_code if exc.response is not None else 502
        if status_code == 404:
            return JsonResponse({'error': 'Pokemon no encontrado.'}, status=404)
        return JsonResponse({'error': 'No se pudo obtener el Pokemon.'}, status=502)
    except requests.RequestException:
        return JsonResponse({'error': 'No se pudo obtener el Pokemon.'}, status=502)
