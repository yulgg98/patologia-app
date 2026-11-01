// Pruebas de "npm run e2e". Se ejecutan con: npm test (desde la raíz del proyecto).
// Solo prueban la preparación; Cypress y los servidores se ejecutan con npm run e2e.
import assert from 'node:assert/strict';
import path from 'node:path';
import { test } from 'node:test';
import {
  ARCHIVO_BASE,
  PUERTO_BACKEND,
  PUERTO_FRONTEND,
  argumentosCypress,
  entornoBackend,
  entornoCypress,
  leerArgumentos,
  pasosPreparacion,
  servidores,
} from './e2e.mjs';

const RAIZ = path.join('C:', 'proyecto');

test('el backend de las pruebas usa su propia base y no la de desarrollo', () => {
  const entorno = entornoBackend({ SECRET_KEY: 'x' });
  assert.equal(entorno.SQLITE_NOMBRE, ARCHIVO_BASE);
  assert.notEqual(ARCHIVO_BASE, 'db.sqlite3');
  assert.equal(entorno.SECRET_KEY, 'x');
});

test('solo sube el límite de peticiones por usuario, permite su frontend y escribe la salida en UTF-8', () => {
  const entorno = entornoBackend({});
  assert.equal(entorno.LIMITE_PETICIONES_USUARIO, '2000/minute');
  // Sin UTF-8, las tildes del registro salen mal en Windows ("Inicio de sesi�n").
  assert.equal(entorno.PYTHONIOENCODING, 'utf-8');
  assert.deepEqual(Object.keys(entorno).sort(), [
    'CORS_ALLOWED_ORIGINS',
    'LIMITE_PETICIONES_USUARIO',
    'PYTHONIOENCODING',
    'SQLITE_NOMBRE',
  ]);
});

test('el backend de las pruebas acepta el origen de su frontend (D-19)', () => {
  const origenes = entornoBackend({}).CORS_ALLOWED_ORIGINS.split(',');
  assert.deepEqual(origenes, [`http://localhost:${PUERTO_FRONTEND}`, `http://127.0.0.1:${PUERTO_FRONTEND}`]);
});

test('prepara la base con migrate y seed_data, con el Python del venv', () => {
  const pasos = pasosPreparacion(RAIZ, 'win32');
  assert.deepEqual(
    pasos.map(({ args }) => args[1]),
    ['migrate', 'seed_data'],
  );
  assert.ok(pasos.every(({ comando }) => comando === path.join(RAIZ, 'backend', 'venv', 'Scripts', 'python.exe')));
  assert.ok(pasos.every(({ cwd }) => cwd === path.join(RAIZ, 'backend')));
});

test('los servidores usan otros puertos que npm run dev y el frontend apunta al backend de las pruebas', () => {
  const [backend, frontend] = servidores(RAIZ, 'linux', {});
  assert.equal(PUERTO_BACKEND, 8001);
  assert.equal(PUERTO_FRONTEND, 5174);
  assert.match(backend.command, /runserver 8001 --noreload$/);
  assert.equal(backend.env.SQLITE_NOMBRE, ARCHIVO_BASE);
  assert.match(frontend.command, /--port 5174 --strictPort$/);
  assert.equal(frontend.env.API_PROXY_DESTINO, 'http://127.0.0.1:8001');
  // El frontend no necesita las variables del backend.
  assert.equal(frontend.env.SQLITE_NOMBRE, undefined);
});

test('Cypress se ejecuta sin ELECTRON_RUN_AS_NODE, que lo dejaría sin arrancar', () => {
  const entorno = entornoCypress({ ELECTRON_RUN_AS_NODE: '1', PATH: 'algo' });
  assert.equal(entorno.ELECTRON_RUN_AS_NODE, undefined);
  assert.equal(entorno.PATH, 'algo');
});

test('"run" sin interfaz, "open" con Chrome y "video" graba; los argumentos extra pasan a Cypress', () => {
  assert.deepEqual(argumentosCypress('correr'), ['cypress', 'run']);
  assert.deepEqual(argumentosCypress('correr', ['--spec', 'x.cy.js']), ['cypress', 'run', '--spec', 'x.cy.js']);
  assert.deepEqual(argumentosCypress('abrir'), ['cypress', 'open', '--e2e', '--browser', 'chrome']);
  assert.deepEqual(argumentosCypress('video'), ['cypress', 'run', '--config', 'video=true']);
});

test('el modo presentación abre Chrome y le pasa la pausa a Cypress con --expose', () => {
  assert.deepEqual(argumentosCypress('presentacion', [], 500), [
    'cypress',
    'open',
    '--e2e',
    '--browser',
    'chrome',
    '--expose',
    'pausa=500',
  ]);
});

test('--abrir, --video y --presentacion eligen el modo y no pasan a Cypress', () => {
  assert.deepEqual(leerArgumentos([]), { modo: 'correr', pausa: 0, extra: [] });
  assert.deepEqual(leerArgumentos(['--abrir']), { modo: 'abrir', pausa: 0, extra: [] });
  assert.deepEqual(leerArgumentos(['--video', '--spec', 'x.cy.js']), {
    modo: 'video',
    pausa: 0,
    extra: ['--spec', 'x.cy.js'],
  });
});

test('la presentación hace una pausa de 500 ms por defecto, que se cambia con --pausa', () => {
  assert.deepEqual(leerArgumentos(['--presentacion']), { modo: 'presentacion', pausa: 500, extra: [] });
  assert.deepEqual(leerArgumentos(['--presentacion', '--pausa=1000']), {
    modo: 'presentacion',
    pausa: 1000,
    extra: [],
  });
  // Fuera de la presentación, la pausa no se usa: las pruebas normales no se hacen más lentas.
  assert.equal(leerArgumentos(['--pausa=1000']).pausa, 0);
});

test('una pausa que no es un número entero positivo se rechaza con un mensaje claro', () => {
  assert.throws(() => leerArgumentos(['--presentacion', '--pausa=lento']), /--pausa/);
  assert.throws(() => leerArgumentos(['--presentacion', '--pausa=-5']), /--pausa/);
  // Más de 3000 ms chocaría con el autoguardado de los borradores a los 5 s (D-13).
  assert.throws(() => leerArgumentos(['--presentacion', '--pausa=3001']), /3000/);
  assert.equal(leerArgumentos(['--presentacion', '--pausa=3000']).pausa, 3000);
});
