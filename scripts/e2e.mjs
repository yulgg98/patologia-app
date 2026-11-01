// npm run e2e: pruebas de punta a punta con Cypress, contra el backend y el frontend reales.
// 1. Crea desde cero una base SQLite aparte (backend/e2e_db.sqlite3) con seed_data:
//    la base de desarrollo no se toca.
// 2. Arranca el backend (8001) y el frontend (5174), en otros puertos que "npm run dev",
//    para que los dos puedan estar abiertos a la vez.
// 3. Ejecuta Cypress y, al terminar, detiene los dos servidores.
// "npm run e2e:abrir" hace lo mismo, pero abre la interfaz de Cypress en Chrome (para mostrarlo en vivo).
// "npm run e2e:presentacion" la abre igual, con una pausa después de cada acción para que el
// público pueda seguirla: 500 ms, o los que diga --pausa (npm run e2e:presentacion -- --pausa=1000).
// "npm run e2e:video" corre todo sin interfaz y graba un video por archivo de pruebas en
// frontend/cypress/videos/ (respaldo para una presentación). Cypress borra los anteriores.
// Los argumentos extra pasan a Cypress: npm run e2e -- --spec cypress/e2e/login-y-roles.cy.js
import { spawnSync } from 'node:child_process';
import { existsSync, rmSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { entornoPython, revisarEntorno, rutaPython } from './entorno.mjs';

export const PUERTO_BACKEND = 8001;
export const PUERTO_FRONTEND = 5174;
export const ARCHIVO_BASE = 'e2e_db.sqlite3';
export const PAUSA_PRESENTACION = 500;
export const PAUSA_MAXIMA = 3000;
// Chrome y no Electron (el navegador de Cypress), que se cerró de golpe en el computador del
// usuario: para la presentación no se elige el navegador a mano.
const NAVEGADOR = 'chrome';

/**
 * Variables de entorno del backend de las pruebas: su propia base y un límite de peticiones
 * por usuario más alto (Cypress hace en segundos lo que una persona hace en minutos).
 * El límite del login no cambia. La salida va en UTF-8 (entornoPython) para que las tildes del
 * registro no salgan mal en Windows. CORS_ALLOWED_ORIGINS es el frontend de las pruebas (5174):
 * el backend rechaza con 403 las peticiones de cualquier otro origen (D-19).
 */
export function entornoBackend(entorno = process.env) {
  return {
    ...entornoPython(entorno),
    SQLITE_NOMBRE: ARCHIVO_BASE,
    LIMITE_PETICIONES_USUARIO: '2000/minute',
    CORS_ALLOWED_ORIGINS: `http://localhost:${PUERTO_FRONTEND},http://127.0.0.1:${PUERTO_FRONTEND}`,
  };
}

/** Pasos para crear la base desde cero (después de borrar el archivo). */
export function pasosPreparacion(raiz, plataforma = process.platform) {
  const python = rutaPython(raiz, plataforma);
  const cwd = path.join(raiz, 'backend');
  return [
    {
      nombre: 'Crear las tablas (migrate)',
      comando: python,
      args: ['manage.py', 'migrate', '--noinput'],
      cwd,
    },
    {
      nombre: 'Cargar los datos de prueba (seed_data)',
      comando: python,
      args: ['manage.py', 'seed_data'],
      cwd,
    },
  ];
}

/** Los dos servidores, en el formato de concurrently. */
export function servidores(raiz, plataforma = process.platform, entorno = process.env) {
  const python = rutaPython(raiz, plataforma);
  return [
    {
      // --noreload: un solo proceso, que se detiene limpio al terminar.
      command: `"${python}" manage.py runserver ${PUERTO_BACKEND} --noreload`,
      name: 'backend',
      cwd: path.join(raiz, 'backend'),
      env: entornoBackend(entorno),
      prefixColor: 'green',
    },
    {
      // --strictPort: si el puerto está ocupado, falla en vez de usar otro.
      command: `npm run dev -- --port ${PUERTO_FRONTEND} --strictPort`,
      name: 'frontend',
      cwd: path.join(raiz, 'frontend'),
      env: {
        ...entorno,
        API_PROXY_DESTINO: `http://127.0.0.1:${PUERTO_BACKEND}`,
      },
      prefixColor: 'cyan',
    },
  ];
}

/**
 * Variables de entorno de Cypress. Las terminales de VS Code (y Claude Code dentro de él)
 * definen ELECTRON_RUN_AS_NODE=1, y con ella Cypress, que es una app de Electron, no
 * arranca ("bad option: --smoke-test"). Por eso se quita.
 */
export function entornoCypress(entorno = process.env) {
  const copia = { ...entorno };
  delete copia.ELECTRON_RUN_AS_NODE;
  return copia;
}

/**
 * Argumentos de Cypress según el modo: 'correr' (sin interfaz), 'abrir' (con ella, en Chrome),
 * 'presentacion' (como abrir, con la pausa) o 'video'. La pausa le llega a las pruebas con
 * --expose, y cypress/support/e2e.js la lee con Cypress.expose('pausa').
 */
export function argumentosCypress(modo, extra = [], pausa = 0) {
  const abrir = ['cypress', 'open', '--e2e', '--browser', NAVEGADOR];
  if (modo === 'abrir') return [...abrir, ...extra];
  if (modo === 'presentacion') return [...abrir, '--expose', `pausa=${pausa}`, ...extra];
  if (modo === 'video') return ['cypress', 'run', '--config', 'video=true', ...extra];
  return ['cypress', 'run', ...extra];
}

const MODOS = { '--abrir': 'abrir', '--video': 'video', '--presentacion': 'presentacion' };

/**
 * El modo sale de --abrir, --video o --presentacion (los pone package.json), y la pausa de
 * --pausa=N, que solo se usa en la presentación: las demás corridas no se hacen más lentas.
 * Lo demás pasa a Cypress.
 */
export function leerArgumentos(argumentos) {
  const opcionModo = argumentos.find((arg) => MODOS[arg]);
  const modo = opcionModo ? MODOS[opcionModo] : 'correr';
  const opcionPausa = argumentos.find((arg) => arg.startsWith('--pausa='));
  let pausa = 0;
  if (modo === 'presentacion') {
    pausa = PAUSA_PRESENTACION;
    if (opcionPausa) {
      const valor = opcionPausa.slice('--pausa='.length);
      if (!/^\d+$/.test(valor)) {
        throw new Error(`--pausa debe ser un número entero de milisegundos (por ejemplo --pausa=800), no "${valor}".`);
      }
      pausa = Number(valor);
      // Con más, una prueba de "Guardar y salir" podría encontrar el borrador ya autoguardado
      // (a los 5 s del último cambio, D-13) y no ver el aviso.
      if (pausa > PAUSA_MAXIMA) {
        throw new Error(`--pausa admite hasta ${PAUSA_MAXIMA} ms (el autoguardado de los borradores es a los 5 s).`);
      }
    }
  }
  const extra = argumentos.filter((arg) => !MODOS[arg] && arg !== opcionPausa);
  return { modo, pausa, extra };
}

/** Espera a que la dirección responda (con cualquier código HTTP). */
async function esperar(url, segundos = 60) {
  for (let i = 0; i < segundos * 2; i++) {
    try {
      await fetch(url);
      return true;
    } catch {
      await new Promise((resolver) => setTimeout(resolver, 500));
    }
  }
  return false;
}

// Solo se ejecuta si se llama directamente (npm run e2e), no al importarlo en las pruebas.
if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const raiz = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
  let modo, pausa, extra;
  try {
    ({ modo, pausa, extra } = leerArgumentos(process.argv.slice(2)));
  } catch (error) {
    console.error(`\n${error.message}\n`);
    process.exit(1);
  }

  const { errores } = revisarEntorno({ raiz, existe: existsSync });
  if (errores.length > 0) {
    console.error('\nFalta preparar el entorno. Ejecuta "npm run dev" para ver qué falta.\n');
    process.exit(1);
  }

  // 1. Base de datos nueva.
  console.log(`\n=== Base de datos de las pruebas (backend/${ARCHIVO_BASE}) ===`);
  rmSync(path.join(raiz, 'backend', ARCHIVO_BASE), { force: true });
  for (const { nombre, comando, args, cwd } of pasosPreparacion(raiz)) {
    console.log(nombre);
    const { status } = spawnSync(comando, args, {
      cwd,
      env: entornoBackend(),
      stdio: ['ignore', 'ignore', 'inherit'],
    });
    if (status !== 0) {
      console.error(`\nFalló: ${nombre}`);
      process.exit(1);
    }
  }

  // 2. Servidores.
  const { default: concurrently } = await import('concurrently');
  const { result, commands } = concurrently(servidores(raiz), {
    killOthersOn: ['failure'],
  });
  let detenidos = false;
  result.catch(() => {
    if (!detenidos) {
      console.error('\nUn servidor se detuvo. ¿Están ocupados los puertos 8001 o 5174?\n');
      process.exit(1);
    }
  });
  // Hay que esperar a que los servidores se cierren antes de salir: si el script termina
  // antes, quedan vivos (en Windows) y la base sigue abierta para la próxima corrida.
  const detener = async () => {
    detenidos = true;
    commands.forEach((comando) => comando.kill());
    await Promise.race([result.catch(() => {}), new Promise((resolver) => setTimeout(resolver, 10000))]);
  };

  const listos =
    (await esperar(`http://127.0.0.1:${PUERTO_BACKEND}/api/`)) &&
    (await esperar(`http://localhost:${PUERTO_FRONTEND}/`));
  if (!listos) {
    console.error('\nLos servidores no respondieron a tiempo.\n');
    await detener();
    process.exit(1);
  }

  // 3. Cypress. En Windows, npx es un .cmd y necesita la terminal (como en check.mjs).
  console.log('\n=== Cypress ===');
  const { status } = spawnSync(`npx ${argumentosCypress(modo, extra, pausa).join(' ')}`, {
    cwd: path.join(raiz, 'frontend'),
    env: entornoCypress(),
    stdio: 'inherit',
    shell: true,
  });
  console.log(
    "\n=== Deteniendo los servidores (en Windows es normal ver 'exited with code 1': es el apagado, no un fallo) ===",
  );
  await detener();
  if (modo === 'video') console.log('\nVideos: frontend/cypress/videos/ (uno por archivo de pruebas).');
  process.exit(status ?? 1);
}
