<template>
  <div class="app">
    <Login v-if="!loggedIn" @login-success="loadDevices" />
    <el-container v-else class="main">
      <el-aside width="280px" class="aside">
        <Devices
          :devices="devices"
          :current="current ? current.id : ''"
          @refresh="loadDevices"
          @select="selectDevice"
          @logout="doLogout"
        />
      </el-aside>
      <el-main>
        <Remote
          v-if="current"
          :key="current.id"
          :device="current"
          @refresh="loadDevices"
        />
        <el-empty v-else description="在左侧选择一台电视" />
      </el-main>
    </el-container>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import Login from './views/Login.vue'
import Devices from './views/Devices.vue'
import Remote from './views/Remote.vue'
import { listDevices, logout } from './api'

const loggedIn = ref(false)
const devices = ref([])
const current = ref(null)

async function loadDevices() {
  try {
    const d = await listDevices()
    devices.value = d.devices
    loggedIn.value = true
    if (current.value) {
      current.value = devices.value.find((x) => x.id === current.value.id) || null
    }
  } catch (e) {
    loggedIn.value = false
  }
}

function selectDevice(dev) {
  current.value = dev
}

async function doLogout() {
  try {
    await logout()
  } catch (e) {
    /* ignore */
  }
  loggedIn.value = false
  devices.value = []
  current.value = null
}

onMounted(loadDevices)
</script>

<style>
html, body, #app { height: 100%; margin: 0; }
body { background: #f5f7fa; }
.app { height: 100%; }
.main { height: 100%; }
.aside { background: #fff; border-right: 1px solid #ebeef5; }
</style>
