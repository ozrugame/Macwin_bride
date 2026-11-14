/* Headless capability probe: device creation is not a rendering/gameplay test. */
#include <windows.h>
#include <stdio.h>
typedef HRESULT (WINAPI *CreateDevice)(void *, unsigned int, HMODULE, unsigned int,
    const unsigned int *, unsigned int, unsigned int, void **, unsigned int *, void **);
static void release(void *object) {
    if (object) {
        void **table = *(void ***)object;
        ((ULONG (WINAPI *)(void *))table[2])(object);
    }
}
int main(void) {
    HMODULE module = LoadLibraryA("d3d11.dll");
    CreateDevice create;
    unsigned int levels[] = {0xb000,0xa100,0xa000,0x9300,0x9200,0x9100}, actual = 0;
    void *device = NULL, *context = NULL;
    HRESULT result;
    if (!module) { printf("LoadLibrary error=%lu\n", GetLastError()); return 2; }
    create = (CreateDevice)GetProcAddress(module, "D3D11CreateDevice");
    if (!create) { puts("D3D11CreateDevice missing"); FreeLibrary(module); return 3; }
    result = create(NULL, 1, NULL, 0, levels, 6, 7, &device, &actual, &context);
    printf("D3D11CreateDevice HRESULT=0x%08lx featureLevel=0x%04x\n", (unsigned long)result, actual);
    release(context); release(device); FreeLibrary(module);
    return result >= 0 && actual >= 0xb000 ? 0 : 1;
}
