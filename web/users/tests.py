from django.contrib.auth.models import User
from unittest.mock import Mock, patch

import requests
from django.test import TestCase
from django.urls import reverse


class PokemonViewsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='ash', password='pikachu123')

    def test_login_view_renders(self):
        response = self.client.get(reverse('login'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Login')

    def test_home_requires_login(self):
        response = self.client.get(reverse('home'))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response.url)

    def test_battle_requires_login(self):
        response = self.client.get(reverse('battle'))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response.url)

    @patch('users.views.requests.get')
    def test_home_view_renders_paginated_pokemon(self, mock_get):
        self.client.login(username='ash', password='pikachu123')

        list_response = Mock()
        list_response.json.return_value = {
            'count': 40,
            'results': [
                {'name': 'bulbasaur', 'url': 'https://pokeapi.co/api/v2/pokemon/1/'},
                {'name': 'ivysaur', 'url': 'https://pokeapi.co/api/v2/pokemon/2/'},
            ],
        }
        list_response.raise_for_status.return_value = None

        type_response = Mock()
        type_response.json.return_value = {
            'results': [{'name': 'grass'}, {'name': 'fire'}],
        }
        type_response.raise_for_status.return_value = None
        mock_get.side_effect = [type_response, list_response]

        response = self.client.get(reverse('home'), {'page': 2})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Pokemon Searcher')
        self.assertContains(response, 'bulbasaur')
        self.assertContains(response, 'Cargar mas')
        self.assertContains(response, 'Mostrando 40 de 40 Pokemon.')
        self.assertContains(response, 'data-load-more')
        self.assertContains(response, 'Buscar por nombre')
        self.assertContains(response, 'grass')

    @patch('users.views.requests.get')
    def test_pokemon_list_api_returns_json(self, mock_get):
        self.client.login(username='ash', password='pikachu123')

        mock_response = Mock()
        mock_response.json.return_value = {
            'count': 2,
            'results': [
                {'name': 'ditto', 'url': 'https://pokeapi.co/api/v2/pokemon/132/'},
            ],
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        response = self.client.get(reverse('pokemon-list-api'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['results'][0]['name'], 'ditto')
        self.assertIn('image', response.json()['results'][0])
        self.assertIn('loaded_count', response.json())

    @patch('users.views.requests.get')
    def test_pokemon_list_api_filters_by_type(self, mock_get):
        self.client.login(username='ash', password='pikachu123')

        mock_response = Mock()
        mock_response.json.return_value = {
            'pokemon': [
                {'pokemon': {'name': 'bulbasaur', 'url': 'https://pokeapi.co/api/v2/pokemon/1/'}},
                {'pokemon': {'name': 'ivysaur', 'url': 'https://pokeapi.co/api/v2/pokemon/2/'}},
            ],
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        response = self.client.get(reverse('pokemon-list-api'), {'type': 'grass'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['count'], 2)
        self.assertEqual(response.json()['results'][0]['name'], 'bulbasaur')

    @patch('users.views.requests.get')
    def test_pokemon_detail_view_renders_details(self, mock_get):
        self.client.login(username='ash', password='pikachu123')

        mock_response = Mock()
        mock_response.json.return_value = {
            'id': 25,
            'name': 'pikachu',
            'height': 4,
            'weight': 60,
            'types': [{'type': {'name': 'electric'}}],
            'abilities': [{'ability': {'name': 'static'}}],
            'sprites': {'front_default': 'https://pokeapi.co/media/sprites/pokemon/25.png'},
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        response = self.client.get(reverse('pokemon-detail', args=['pikachu']))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'pikachu')
        self.assertContains(response, 'electric')
        self.assertContains(response, 'static')

    @patch('users.views.requests.get')
    def test_pokemon_detail_api_returns_not_found(self, mock_get):
        self.client.login(username='ash', password='pikachu123')

        mock_response = Mock(status_code=404)
        error = requests.HTTPError(response=mock_response)
        mock_get.return_value.raise_for_status.side_effect = error

        response = self.client.get(reverse('pokemon-detail-api', args=['missingno']))

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()['error'], 'Pokemon no encontrado.')

    @patch('users.views.random.choice', return_value='attack')
    @patch('users.views.random.randint', return_value=10)
    @patch('users.views.random.random', return_value=0.5)
    @patch('users.views.requests.get')
    def test_battle_view_renders_winner(self, mock_get, _random_value, _randint, _choice):
        self.client.login(username='ash', password='pikachu123')

        names_response = Mock()
        names_response.json.return_value = {
            'results': [{'name': 'pikachu'}, {'name': 'bulbasaur'}],
        }
        names_response.raise_for_status.return_value = None

        pikachu_response = Mock()
        pikachu_response.json.return_value = {
            'id': 25,
            'name': 'pikachu',
            'height': 4,
            'weight': 60,
            'types': [{'type': {'name': 'electric'}}],
            'abilities': [{'ability': {'name': 'static'}}],
            'stats': [
                {'base_stat': 35, 'stat': {'name': 'hp'}},
                {'base_stat': 55, 'stat': {'name': 'attack'}},
                {'base_stat': 40, 'stat': {'name': 'defense'}},
                {'base_stat': 50, 'stat': {'name': 'special-attack'}},
                {'base_stat': 50, 'stat': {'name': 'special-defense'}},
                {'base_stat': 90, 'stat': {'name': 'speed'}},
            ],
            'sprites': {'front_default': 'https://pokeapi.co/media/sprites/pokemon/25.png'},
        }
        pikachu_response.raise_for_status.return_value = None

        bulbasaur_response = Mock()
        bulbasaur_response.json.return_value = {
            'id': 1,
            'name': 'bulbasaur',
            'height': 7,
            'weight': 69,
            'types': [{'type': {'name': 'grass'}}],
            'abilities': [{'ability': {'name': 'overgrow'}}],
            'stats': [
                {'base_stat': 45, 'stat': {'name': 'hp'}},
                {'base_stat': 49, 'stat': {'name': 'attack'}},
                {'base_stat': 49, 'stat': {'name': 'defense'}},
                {'base_stat': 65, 'stat': {'name': 'special-attack'}},
                {'base_stat': 65, 'stat': {'name': 'special-defense'}},
                {'base_stat': 45, 'stat': {'name': 'speed'}},
            ],
            'sprites': {'front_default': 'https://pokeapi.co/media/sprites/pokemon/1.png'},
        }
        bulbasaur_response.raise_for_status.return_value = None

        mock_get.side_effect = [names_response, pikachu_response, bulbasaur_response]

        response = self.client.post(reverse('battle'), {
            'first_pokemon': 'pikachu',
            'second_pokemon': 'bulbasaur',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ganador')
        self.assertContains(response, 'Pasos de la pelea')
