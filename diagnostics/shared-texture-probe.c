/* Qualifies creation/export of one shared D3D11 texture, not rendering. */
#include <windows.h>
#include <stdio.h>
typedef HRESULT (WINAPI *CreateDevice)(void *, unsigned int, HMODULE, unsigned int,
    const unsigned int *, unsigned int, unsigned int, void **, unsigned int *, void **);
typedef struct {
    unsigned int width, height, mipLevels, arraySize, format;
    unsigned int sampleCount, sampleQuality, usage, bindFlags, cpuAccess, miscFlags;
} TextureDesc;
static void release(void *object) {
    if (object) ((ULONG (WINAPI *)(void *))(*(void ***)object)[2])(object);
}
int main(void) {
    static const GUID resourceIID = {0x035f3ab4,0x482e,0x4e50,{0xb4,0x1f,0x8a,0x7f,0x8b,0xd8,0x96,0x0b}};
    HMODULE module = LoadLibraryA("d3d11.dll");
    unsigned int levels[] = {0xb000}, actual = 0;
    void *device = NULL, *context = NULL, *texture = NULL, *resource = NULL;
    TextureDesc desc = {64,64,1,1,28,1,0,0,40,0,2};
    HANDLE handle = NULL;
    HRESULT result;
    CreateDevice create;
    int status = 1;
    if (!module) return 2;
    create = (CreateDevice)GetProcAddress(module, "D3D11CreateDevice");
    if (!create) { FreeLibrary(module); return 3; }
    result = create(NULL,1,NULL,0,levels,1,7,&device,&actual,&context);
    printf("CreateDevice: 0x%08lx level=0x%04x\n", (unsigned long)result, actual);
    if (result < 0) goto done;
    result = ((HRESULT (WINAPI *)(void *, const TextureDesc *, const void *, void **))
        (*(void ***)device)[5])(device,&desc,NULL,&texture);
    printf("CreateTexture2D(SHARED): 0x%08lx\n", (unsigned long)result);
    if (result < 0) goto done;
    result = ((HRESULT (WINAPI *)(void *, const GUID *, void **))
        (*(void ***)texture)[0])(texture,&resourceIID,&resource);
    if (result < 0) goto done;
    result = ((HRESULT (WINAPI *)(void *, HANDLE *))
        (*(void ***)resource)[8])(resource,&handle);
    printf("GetSharedHandle: 0x%08lx nonnull=%d\n", (unsigned long)result, handle != NULL);
    status = result >= 0 && handle != NULL ? 0 : 1;
done:
    /* Legacy shared handles are not NT handles and must not be CloseHandle'd. */
    release(resource); release(texture); release(context); release(device);
    FreeLibrary(module);
    return status;
}
